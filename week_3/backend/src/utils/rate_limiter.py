import os

def get_model_limits(model_name: str):
    """
    Parses .rate_limits.txt and calculates batching/cooldown values.
    Returns: (batch_size, retry_cooldown)
    """
    # 1. Default fallback values
    rpm, tpm = 5, 250000 
    
    # 2. Locate the file correctly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Adjust this path if your .rate_limits.txt is in a different location relative to this file
    file_path = os.path.join(current_dir, "..", ".rate_limits.txt")
    
    # 3. Parse the file
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                for line in f:
                    parts = line.split()
                    if parts and parts[0] == model_name:
                        rpm = int(parts[1])
                        tpm = int(parts[2].replace('K', '000'))
                        break
    except Exception as e:
        print(f"Rate Limiter Warning: Could not read file: {e}")

    # 4. Perform the Math
    # BATCH_SIZE = (tpm / rpm) * 0.8 / 1000
    # We round down to ensure we stay safely under the limit
    batch_size = int((tpm / rpm) * 0.8 / 1000)
    
    # RETRY_COOLDOWN = 60 / rpm
    retry_cooldown = 60 / rpm
    
    return batch_size, retry_cooldown