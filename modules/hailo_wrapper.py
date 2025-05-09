import os
import sys
import logging
import importlib.util
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)

# Ensure the Hailo libraries are in the system path
hailo_lib_path = '/usr/lib'
if hailo_lib_path not in os.environ.get('LD_LIBRARY_PATH', '').split(':'):
    os.environ['LD_LIBRARY_PATH'] = ':'.join([hailo_lib_path, os.environ.get('LD_LIBRARY_PATH', '')])

# Try to import Hailo SDK
try:
    import hailo
    import hailort
    HAILO_AVAILABLE = True
    logging.info("Hailo SDK successfully imported")
except ImportError:
    try:
        # Try alternative paths for Hailo SDK
        sys.path.append('/home/automate/.local/lib/python3.11/site-packages')
        import hailo
        import hailort
        HAILO_AVAILABLE = True
        logging.info("Hailo SDK successfully imported from alternate path")
    except ImportError:
        logging.error("Hailo SDK could not be imported. Detection will be simulated.")
        HAILO_AVAILABLE = False

class HailoWrapper:
    def __init__(self, model_path):
        self.model_path = model_path
        self.device = None
        self.network = None
        self.input_vstream = None
        self.output_vstream = None
        self.initialized = False
        self.input_shape = None
        self.output_shape = None
        
        if not HAILO_AVAILABLE:
            logging.error("Hailo SDK not available. Cannot initialize Hailo device.")
            return
            
        if not os.path.exists(self.model_path):
            logging.error(f"Model file not found: {self.model_path}")
            return
            
        try:
            # Initialize Hailo device
            self.device = hailort.Device()
            logging.info(f"Initialized Hailo device: {self.device.get_devname()}")
            
            # Load the network onto the device
            self.network = self.device.load_network(self.model_path)
            logging.info(f"Loaded model: {self.model_path}")
            
            # Get input and output tensors info
            input_tensors = self.network.get_input_tensors()
            output_tensors = self.network.get_output_tensors()
            
            if not input_tensors or not output_tensors:
                logging.error("No input or output tensors found in the model")
                return
                
            self.input_shape = input_tensors[0].shape()
            self.output_shape = output_tensors[0].shape()
            
            logging.info(f"Model input shape: {self.input_shape}")
            logging.info(f"Model output shape: {self.output_shape}")
            
            # Setup input and output virtual streams
            self.input_vstream = self.network.create_input_vstream()
            self.output_vstream = self.network.create_output_vstream()
            
            self.initialized = True
            logging.info("Hailo device initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Hailo device: {e}")
            self.cleanup()
    
    def infer(self, image):
        if not self.initialized:
            logging.error("Hailo device not initialized. Cannot perform inference.")
            return None
            
        try:
            # Preprocess image
            preprocessed_image = self.preprocess_image(image)
            
            # Write input data to device
            self.input_vstream.write(preprocessed_image)
            
            # Read output data from device
            output_data = self.output_vstream.read()
            
            # Post-process output data
            results = self.postprocess_output(output_data)
            
            return results
        except Exception as e:
            logging.error(f"Error during Hailo inference: {e}")
            return None
    
    def preprocess_image(self, image):
        """Preprocess the image for Hailo inference"""
        try:
            # Resize image to match model input shape
            if self.input_shape and len(self.input_shape) >= 3:
                height, width = self.input_shape[1], self.input_shape[2]
                resized_image = cv2.resize(image, (width, height))
            else:
                # Default to 640x640 for YOLO models if shape is not available
                resized_image = cv2.resize(image, (640, 640))
            
            # Convert to RGB if needed
            if len(resized_image.shape) == 3 and resized_image.shape[2] == 3:
                # Already RGB, do nothing
                pass
            else:
                resized_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
            
            # Normalize pixel values to [0,1]
            normalized_image = resized_image.astype(np.float32) / 255.0
            
            # Transpose to model expected format [N,C,H,W]
            input_tensor = np.transpose(normalized_image, (2, 0, 1))
            
            # Add batch dimension
            input_tensor = np.expand_dims(input_tensor, axis=0)
            
            return input_tensor
        except Exception as e:
            logging.error(f"Error preprocessing image: {e}")
            return image
    
    def postprocess_output(self, output_data):
        """Process the raw output from Hailo to bounding boxes"""
        try:
            # This is a simplified implementation
            # Actual implementation depends on the specific model format
            
            # Convert output to numpy array if it's not already
            if not isinstance(output_data, np.ndarray):
                output_data = np.array(output_data)
            
            # For YOLO models, the output is typically:
            # [batch, num_boxes, 5+num_classes] where 5 is [x, y, w, h, confidence]
            
            # Filter out low confidence detections
            confidence_threshold = 0.5
            detections = []
            
            # This is a simplified example - adapt based on your model's output format
            if len(output_data.shape) == 3 and output_data.shape[2] > 5:
                for box in output_data[0]:  # Process first batch
                    confidence = box[4]
                    if confidence > confidence_threshold:
                        # Get class with highest probability
                        class_id = np.argmax(box[5:])
                        class_confidence = box[5 + class_id]
                        
                        # Only keep person class (usually class 0)
                        if class_id == 0:  # Assuming 0 is person class
                            x, y, w, h = box[0:4]
                            
                            # Convert to [x1, y1, x2, y2, confidence, class_id]
                            x1 = int(x - w/2)
                            y1 = int(y - h/2)
                            x2 = int(x + w/2)
                            y2 = int(y + h/2)
                            
                            detections.append([x1, y1, x2, y2, confidence, class_id])
            
            return detections
        except Exception as e:
            logging.error(f"Error postprocessing output: {e}")
            return []
    
    def cleanup(self):
        """Release Hailo resources"""
        try:
            if self.input_vstream:
                self.input_vstream.release()
                self.input_vstream = None
            
            if self.output_vstream:
                self.output_vstream.release()
                self.output_vstream = None
            
            if self.network:
                self.network.release()
                self.network = None
            
            if self.device:
                self.device.release()
                self.device = None
                
            logging.info("Hailo resources released")
        except Exception as e:
            logging.error(f"Error during Hailo cleanup: {e}")

def is_hailo_available():
    """Check if Hailo SDK is available"""
    return HAILO_AVAILABLE
