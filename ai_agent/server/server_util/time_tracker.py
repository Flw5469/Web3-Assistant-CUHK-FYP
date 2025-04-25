import time
import functools
import logging

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('time_tracker')

# Global variable to store the timestamp of the previous function call
previous_time = time.time()

def time_tracker(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global previous_time
        
        # Get current time
        current_time = time.time()
        
        # Calculate time elapsed since previous function call
        elapsed = current_time - previous_time
        
        # Update previous_time for the next function call
        previous_time = current_time
        
        # Execute the function
        result = func(*args, **kwargs)
        
        # Log time information
        logger.info(f"Function '{func.__name__}' executed. Time since previous call: {elapsed:.6f} seconds")
        
        return result
    return wrapper