"""
Image Handling Module for Quality System
Handle image uploads, storage, compression, and thumbnails
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os
import hashlib
from datetime import datetime
from typing import Tuple, Optional
import json
from models import ImageAttachment


class ImageHandler:
    """Handle image operations for quality system"""
    
    def __init__(self, session, storage_dir=None):
        """
        Initialize image handler
        
        Args:
            session: SQLAlchemy session
            storage_dir: Directory to store images. If None, uses default.
        """
        self.session = session
        
        if storage_dir is None:
            # Default to user's home directory
            storage_dir = Path.home() / '.quality_system' / 'images'
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.records_dir = self.storage_dir / 'records'
        self.items_dir = self.storage_dir / 'items'
        self.nc_dir = self.storage_dir / 'non_conformances'
        self.thumbnails_dir = self.storage_dir / 'thumbnails'
        
        for directory in [self.records_dir, self.items_dir, self.nc_dir, self.thumbnails_dir]:
            directory.mkdir(exist_ok=True)
    
    def save_image(self, image_path: str, entity_type: str, entity_id: int,
                  description: str = None, tags: list = None,
                  uploaded_by_id: int = None,
                  max_size: Tuple[int, int] = (1920, 1920),
                  create_thumbnail: bool = True) -> ImageAttachment:
        """
        Save an image to the system
        
        Args:
            image_path: Path to the image file
            entity_type: Type of entity ('record', 'record_item', 'non_conformance')
            entity_id: ID of the entity
            description: Image description
            tags: List of tags for the image
            uploaded_by_id: User ID who uploaded the image
            max_size: Maximum image dimensions (width, height)
            create_thumbnail: Whether to create a thumbnail
            
        Returns:
            ImageAttachment object
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load and process image
        img = Image.open(image_path)
        
        # Convert to RGB if needed (for saving as JPEG)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Resize if too large
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_filename = Path(image_path).name
        file_hash = hashlib.md5(f"{entity_type}_{entity_id}_{timestamp}".encode()).hexdigest()[:8]
        filename = f"{entity_type}_{entity_id}_{timestamp}_{file_hash}.jpg"
        
        # Determine storage directory
        if entity_type == 'record':
            target_dir = self.records_dir
        elif entity_type == 'record_item':
            target_dir = self.items_dir
        elif entity_type == 'non_conformance':
            target_dir = self.nc_dir
        else:
            target_dir = self.storage_dir
        
        # Save processed image
        file_path = target_dir / filename
        img.save(file_path, 'JPEG', quality=85, optimize=True)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create thumbnail if requested
        thumbnail_path = None
        if create_thumbnail:
            thumbnail_path = self._create_thumbnail(img, filename)
        
        # Create database record
        image_attachment = ImageAttachment(
            entity_type=entity_type,
            entity_id=entity_id,
            filename=filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type='image/jpeg',
            width=img.width,
            height=img.height,
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            description=description,
            tags=tags,
            uploaded_by_id=uploaded_by_id
        )
        
        self.session.add(image_attachment)
        self.session.commit()
        
        return image_attachment
    
    def _create_thumbnail(self, img: Image.Image, filename: str, 
                         size: Tuple[int, int] = (200, 200)) -> Path:
        """
        Create thumbnail from image
        
        Args:
            img: PIL Image object
            filename: Original filename
            size: Thumbnail size (width, height)
            
        Returns:
            Path to thumbnail file
        """
        # Create copy for thumbnail
        thumb = img.copy()
        thumb.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        thumb_filename = f"thumb_{filename}"
        thumb_path = self.thumbnails_dir / thumb_filename
        thumb.save(thumb_path, 'JPEG', quality=75, optimize=True)
        
        return thumb_path
    
    def get_image(self, image_id: int) -> Optional[ImageAttachment]:
        """
        Get image attachment by ID
        
        Args:
            image_id: ImageAttachment ID
            
        Returns:
            ImageAttachment object or None
        """
        return self.session.query(ImageAttachment).get(image_id)
    
    def get_images_for_entity(self, entity_type: str, entity_id: int) -> list:
        """
        Get all images for a specific entity
        
        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            
        Returns:
            List of ImageAttachment objects
        """
        return self.session.query(ImageAttachment).filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(ImageAttachment.uploaded_at.desc()).all()
    
    def delete_image(self, image_id: int, delete_file: bool = True):
        """
        Delete an image
        
        Args:
            image_id: ImageAttachment ID
            delete_file: Whether to also delete the file from disk
        """
        image = self.get_image(image_id)
        
        if not image:
            return
        
        # Delete files if requested
        if delete_file:
            # Delete main file
            if image.file_path and os.path.exists(image.file_path):
                os.remove(image.file_path)
            
            # Delete thumbnail
            if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                os.remove(image.thumbnail_path)
        
        # Delete database record
        self.session.delete(image)
        self.session.commit()
    
    def add_watermark(self, image_path: str, text: str, output_path: str = None) -> str:
        """
        Add watermark to an image
        
        Args:
            image_path: Path to input image
            text: Watermark text
            output_path: Path to output image. If None, overwrites input.
            
        Returns:
            Path to watermarked image
        """
        if output_path is None:
            output_path = image_path
        
        # Open image
        img = Image.open(image_path)
        
        # Create drawing context
        draw = ImageDraw.Draw(img)
        
        # Use default font (or specify font path)
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        # Calculate text position (bottom right)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        margin = 20
        x = img.width - text_width - margin
        y = img.height - text_height - margin
        
        # Draw semi-transparent background
        draw.rectangle(
            [(x - 10, y - 10), (x + text_width + 10, y + text_height + 10)],
            fill=(255, 255, 255, 128)
        )
        
        # Draw text
        draw.text((x, y), text, fill=(0, 0, 0, 200), font=font)
        
        # Save image
        img.save(output_path, 'JPEG', quality=90)
        
        return output_path
    
    def compress_image(self, image_path: str, output_path: str = None, 
                      quality: int = 85) -> str:
        """
        Compress an image
        
        Args:
            image_path: Path to input image
            output_path: Path to output image. If None, overwrites input.
            quality: JPEG quality (0-100)
            
        Returns:
            Path to compressed image
        """
        if output_path is None:
            output_path = image_path
        
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        img.save(output_path, 'JPEG', quality=quality, optimize=True)
        
        return output_path
    
    def create_comparison_image(self, before_path: str, after_path: str, 
                               output_path: str) -> str:
        """
        Create a side-by-side comparison image
        
        Args:
            before_path: Path to "before" image
            after_path: Path to "after" image
            output_path: Path to output comparison image
            
        Returns:
            Path to comparison image
        """
        # Load images
        img_before = Image.open(before_path)
        img_after = Image.open(after_path)
        
        # Resize to same height
        target_height = min(img_before.height, img_after.height, 800)
        
        aspect_before = img_before.width / img_before.height
        aspect_after = img_after.width / img_after.height
        
        img_before = img_before.resize(
            (int(target_height * aspect_before), target_height),
            Image.Resampling.LANCZOS
        )
        img_after = img_after.resize(
            (int(target_height * aspect_after), target_height),
            Image.Resampling.LANCZOS
        )
        
        # Create combined image
        total_width = img_before.width + img_after.width + 20  # 20px gap
        combined = Image.new('RGB', (total_width, target_height + 60), (255, 255, 255))
        
        # Paste images
        combined.paste(img_before, (0, 30))
        combined.paste(img_after, (img_before.width + 20, 30))
        
        # Add labels
        draw = ImageDraw.Draw(combined)
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((img_before.width // 2 - 30, 5), "BEFORE", fill=(0, 0, 0), font=font)
        draw.text((img_before.width + 20 + img_after.width // 2 - 25, 5), "AFTER", fill=(0, 0, 0), font=font)
        
        # Save
        combined.save(output_path, 'JPEG', quality=90)
        
        return output_path
    
    def annotate_image(self, image_path: str, annotations: list, 
                      output_path: str = None) -> str:
        """
        Add annotations (rectangles, arrows, text) to an image
        
        Args:
            image_path: Path to input image
            annotations: List of annotation dictionaries with format:
                        {'type': 'rect'|'circle'|'text', 'coords': [...], 'text': '...', 'color': '...'}
            output_path: Path to output image. If None, overwrites input.
            
        Returns:
            Path to annotated image
        """
        if output_path is None:
            output_path = image_path
        
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        for annotation in annotations:
            ann_type = annotation.get('type', 'rect')
            coords = annotation.get('coords', [])
            text = annotation.get('text', '')
            color = annotation.get('color', 'red')
            
            if ann_type == 'rect' and len(coords) == 4:
                # Draw rectangle
                draw.rectangle(coords, outline=color, width=3)
                if text:
                    draw.text((coords[0], coords[1] - 25), text, fill=color, font=font)
            
            elif ann_type == 'circle' and len(coords) == 3:
                # Draw circle (coords: [center_x, center_y, radius])
                x, y, r = coords
                draw.ellipse([x - r, y - r, x + r, y + r], outline=color, width=3)
                if text:
                    draw.text((x - r, y - r - 25), text, fill=color, font=font)
            
            elif ann_type == 'text' and len(coords) == 2:
                # Draw text
                draw.text(coords, text, fill=color, font=font)
        
        img.save(output_path, 'JPEG', quality=90)
        
        return output_path
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage stats
        """
        total_images = self.session.query(ImageAttachment).count()
        total_size = self.session.query(
            func.sum(ImageAttachment.file_size)
        ).scalar() or 0
        
        # Count by entity type
        records_count = self.session.query(ImageAttachment).filter_by(
            entity_type='record'
        ).count()
        
        items_count = self.session.query(ImageAttachment).filter_by(
            entity_type='record_item'
        ).count()
        
        nc_count = self.session.query(ImageAttachment).filter_by(
            entity_type='non_conformance'
        ).count()
        
        return {
            'total_images': total_images,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'records_images': records_count,
            'items_images': items_count,
            'nc_images': nc_count
        }


# Convenience functions
def save_image_for_record(session, image_path, record_id, description=None, uploaded_by_id=None):
    """Quick save image for record"""
    handler = ImageHandler(session)
    return handler.save_image(image_path, 'record', record_id, description, uploaded_by_id=uploaded_by_id)


def save_image_for_nc(session, image_path, nc_id, description=None, uploaded_by_id=None):
    """Quick save image for non-conformance"""
    handler = ImageHandler(session)
    return handler.save_image(image_path, 'non_conformance', nc_id, description, uploaded_by_id=uploaded_by_id)


def get_record_images(session, record_id):
    """Quick get images for record"""
    handler = ImageHandler(session)
    return handler.get_images_for_entity('record', record_id)
