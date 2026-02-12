"""
OpenCV-based camera capture for Linux stability
This avoids the FFmpeg 7.1.2 segfault issue with Qt Multimedia
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QDialog, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from datetime import datetime
import tempfile
from pathlib import Path
import os

class OpenCVCameraDialog(QDialog):
    """Camera dialog using OpenCV instead of Qt Multimedia"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Camera Capture")
        self.setMinimumSize(640, 520)
        self.captured_file = None
        self.camera = None
        self.timer = None
        
        try:
            import cv2
            self.cv2 = cv2
        except ImportError:
            QMessageBox.critical(
                self, 
                "OpenCV Not Installed", 
                "OpenCV is required for camera capture.\n\n"
                "Install it with: pip install opencv-python\n\n"
                "Falling back to Qt Multimedia (may crash on Linux with FFmpeg 7.x)"
            )
            QTimer.singleShot(0, self.reject)
            return
        
        self.setup_ui()
        self.setup_camera()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Video display label
        self.video_label = QLabel()
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black; border: 2px solid #ddd;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(False)
        layout.addWidget(self.video_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.capture_btn = QPushButton("📷 Capture Photo")
        self.capture_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        self.capture_btn.clicked.connect(self.capture_photo)
        controls_layout.addWidget(self.capture_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        controls_layout.addWidget(cancel_btn)
        
        layout.addLayout(controls_layout)
        
    def setup_camera(self):
        try:
            # Open default camera (0)
            self.camera = self.cv2.VideoCapture(0)
            
            if not self.camera.isOpened():
                QMessageBox.critical(self, "Error", "Could not open camera")
                QTimer.singleShot(0, self.reject)
                return
            
            # Set resolution
            self.camera.set(self.cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(self.cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Start timer to update frames
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)  # 30ms = ~33 fps
            
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", f"Failed to initialize camera: {str(e)}")
            QTimer.singleShot(0, self.reject)
    
    def update_frame(self):
        """Update video preview"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                # Convert BGR to RGB
                rgb_frame = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                
                # Convert to QImage
                qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                
                # Scale to fit label while maintaining aspect ratio
                pixmap = QPixmap.fromImage(qt_image)
                scaled_pixmap = pixmap.scaled(
                    self.video_label.size(), 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
                self.video_label.setPixmap(scaled_pixmap)
    
    def capture_photo(self):
        """Capture current frame"""
        if not self.camera or not self.camera.isOpened():
            QMessageBox.warning(self, "Error", "Camera not available")
            return
        
        try:
            self.capture_btn.setEnabled(False)
            self.capture_btn.setText("Capturing...")
            
            # Read current frame
            ret, frame = self.camera.read()
            if not ret:
                QMessageBox.warning(self, "Error", "Failed to capture frame")
                self.capture_btn.setEnabled(True)
                self.capture_btn.setText("📷 Capture Photo")
                return
            
            # Save to temp file
            temp_dir = Path(tempfile.gettempdir())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = temp_dir / f"captured_{timestamp}.jpg"
            
            # Write image
            success = self.cv2.imwrite(str(save_path), frame)
            
            if success and save_path.exists():
                print(f"Image saved: {save_path}")
                self.captured_file = str(save_path)
                
                # Clean shutdown
                self.cleanup_camera()
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save image")
                self.capture_btn.setEnabled(True)
                self.capture_btn.setText("📷 Capture Photo")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Capture failed: {str(e)}")
            self.capture_btn.setEnabled(True)
            self.capture_btn.setText("📷 Capture Photo")
    
    def cleanup_camera(self):
        """Release camera resources"""
        try:
            if self.timer:
                self.timer.stop()
                self.timer = None
            if self.camera:
                self.camera.release()
                self.camera = None
        except:
            pass
    
    def closeEvent(self, event):
        """Handle dialog close"""
        self.cleanup_camera()
        super().closeEvent(event)
    
    def reject(self):
        """Handle cancel"""
        self.cleanup_camera()
        super().reject()
