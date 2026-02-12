
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QDialog, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from datetime import datetime
import os

class CameraCaptureDialog(QDialog):
    """Dialog for capturing photos from camera using PyQt6 Multimedia"""
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QImageCapture, QMediaDevices
            from PyQt6.QtMultimediaWidgets import QVideoWidget
            self.QCamera = QCamera
            self.QMediaCaptureSession = QMediaCaptureSession
            self.QImageCapture = QImageCapture
            self.QMediaDevices = QMediaDevices
            self.QVideoWidget = QVideoWidget
        except ImportError:
            QMessageBox.critical(self, "Error", "Multimedia modules not available. Please install PyQt6-Multimedia.")
            QTimer.singleShot(0, self.reject)
            return

        self.setWindowTitle("Camera Capture")
        self.setMinimumSize(640, 520)
        self.captured_file = None
        
        self.setup_ui()
        self.setup_camera()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Video display
        self.video_widget = self.QVideoWidget()
        self.video_widget.setMinimumSize(640, 480)
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.camera_combo = QComboBox()
        self.cameras = self.QMediaDevices.videoInputs()
        for camera in self.cameras:
            self.camera_combo.addItem(camera.description(), camera)
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        controls_layout.addWidget(QLabel("Camera:"))
        controls_layout.addWidget(self.camera_combo, 1)
        
        self.capture_btn = QPushButton("Capture Photo")
        self.capture_btn.clicked.connect(self.capture_photo)
        self.capture_btn.setStyleSheet("background-color: #2e86de; color: white; font-weight: bold; padding: 10px; height: 30px;")
        controls_layout.addWidget(self.capture_btn)
        
        layout.addLayout(controls_layout)
        
        # Bottom buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def setup_camera(self):
        try:
            from PyQt6.QtMultimedia import QCamera, QMediaCaptureSession, QImageCapture, QMediaDevices
            self.capture_session = self.QMediaCaptureSession()
            
            default_camera = self.QMediaDevices.defaultVideoInput()
            if default_camera.isNull():
                QMessageBox.critical(self, "Error", "No camera detected on this device")
                QTimer.singleShot(0, self.reject)
                return

            self.camera = self.QCamera(default_camera)
            self.image_capture = self.QImageCapture(self.camera)
            
            self.capture_session.setCamera(self.camera)
            self.capture_session.setVideoOutput(self.video_widget)
            self.capture_session.setImageCapture(self.image_capture)
            
            # Connect only memory capture as it's more stable on Linux/FFmpeg 7
            self.image_capture.imageCaptured.connect(self.on_image_captured)
            self.image_capture.errorOccurred.connect(self.on_capture_error)
            
            self.camera.start()
        except Exception as e:
            QMessageBox.critical(self, "Camera Error", f"Failed to initialize camera: {str(e)}")
            QTimer.singleShot(0, self.reject)
        
    def on_capture_error(self, requestId, error, errorString):
        print(f"Capture Error ({error}): {errorString}")
        # Only show error if we haven't already captured the file
        if not self.captured_file:
            QMessageBox.warning(self, "Capture Error", f"Camera Error: {errorString}")
        self.capture_btn.setEnabled(True)
        self.capture_btn.setText("Capture Photo")

    def change_camera(self, index):
        if hasattr(self, 'camera'):
            self.camera.stop()
        camera_info = self.camera_combo.itemData(index)
        self.camera = self.QCamera(camera_info)
        self.capture_session.setCamera(self.camera)
        self.camera.start()
        
    def capture_photo(self):
        try:
            import tempfile
            from pathlib import Path
            temp_dir = Path(tempfile.gettempdir())
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.save_path = str(temp_dir / f"captured_{timestamp}.jpg")
            
            self.capture_btn.setEnabled(False)
            self.capture_btn.setText("Capturing...")
            self.captured_file = None
            
            print(f"Starting memory capture...")
            # Use capture() instead of captureToFile() to avoid FFmpeg file-lock/teardown issues
            self.image_capture.capture()
            
            # Timeout fallback remains
            QTimer.singleShot(4000, self.check_capture_status)
        except Exception as e:
            print(f"Capture exception: {e}")
            QMessageBox.critical(self, "Error", f"Capture failed: {str(e)}")
            self.capture_btn.setEnabled(True)
            self.capture_btn.setText("Capture Photo")

    def check_capture_status(self):
        """Check if capture has finished. If not, try a fallback frame grab."""
        if not self.captured_file:
            print("Capture timed out. Attempting fallback frame grab.")
            try:
                pixmap = self.video_widget.grab()
                if not pixmap.isNull():
                    pixmap.save(self.save_path, "JPG")
                    self.finalize_capture(self.save_path)
                else:
                    raise Exception("Grabbed pixmap is null")
            except Exception as e:
                print(f"Fallback grab failed: {e}")
                self.capture_btn.setEnabled(True)
                self.capture_btn.setText("Capture Photo")

    def on_image_captured(self, requestId, image):
        """Called when image is captured in memory"""
        print(f"Image captured in memory (requestId: {requestId})")
        if not self.captured_file:
            try:
                if image.save(self.save_path, "JPG"):
                    print("Saved memory capture to file.")
                    self.finalize_capture(self.save_path)
            except Exception as e:
                print(f"Memory save failed: {e}")
                self.capture_btn.setEnabled(True)
                self.capture_btn.setText("Capture Photo")

    def finalize_capture(self, path):
        """Safely shutdown camera and accept dialog"""
        if self.captured_file:
            return
            
        print(f"Finalizing capture: {path}")
        self.captured_file = path
        
        # Robust teardown to prevent Linux FFmpeg segfaults
        try:
            if hasattr(self, 'image_capture'):
                self.image_capture.imageCaptured.disconnect()
            if hasattr(self, 'camera'):
                self.camera.stop()
            if hasattr(self, 'capture_session'):
                self.capture_session.setCamera(None)
                self.capture_session.setVideoOutput(None)
        except:
            pass
            
        # Give the backend a moment to release hardware before closing window
        QTimer.singleShot(300, self.accept)

    def on_image_saved(self, requestId, path):
        # We are using manual saving from memory now for stability
        pass
        
    def closeEvent(self, event):
        try:
            if hasattr(self, 'camera'):
                self.camera.stop()
        except:
            pass
        super().closeEvent(event)
        
    def closeEvent(self, event):
        if hasattr(self, 'camera'):
            try:
                self.camera.stop()
            except:
                pass
        super().closeEvent(event)
