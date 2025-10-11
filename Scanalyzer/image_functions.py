import os
import numpy as np
import nanonispy2 as nap
from scipy.signal import convolve2d

def get_scan(file_name, crop_unfinished: bool = True):
    if not os.path.exists(file_name):
        print(f"Error: File \"{file_name}\" does not exist.")
        return
    else:
        scan_data = nap.read.Scan(file_name) # Read the scan data. scan_data is an object whose attributes contain all the data of the scan
        channels = np.array(list(scan_data.signals.keys())) # Read the various channels
        scan_header = scan_data.header
        up_or_down = scan_header.get("scan_dir", "down") # Read whether the scan was recorded in the upward or downward direction
        
        # Stack the forward and backward scans for each channel in a big tensor. Flip the backward scan
        scan_tensor_uncropped = np.stack([np.stack((np.array(scan_data.signals[channel]["forward"], dtype = float), np.flip(np.array(scan_data.signals[channel]["backward"], dtype = float), axis = 1))) for channel in channels])
        if up_or_down == "up": scan_tensor_uncropped = np.flip(scan_tensor_uncropped, axis = 2) # Flip the scan if it recorded in the upward direction

        # Determine which rows should be cropped off in case the scan was not completed
        pixels_uncropped = scan_header.get("scan_pixels", np.array([100, 100], dtype = int)) # Read the old number of pixels in the scan
        scan_range_uncropped = scan_header.get("scan_range", np.array([1E-8, 1E-8], dtype = float)) # Read the old size of the scan
        masked_array = np.isnan(scan_tensor_uncropped[0, 1]) # All channels have the same number of NaN values. The backward scan has more NaN values because the scan always starts in the forward direction.
        nan_counts = np.array([sum([int(masked_array[j, i]) for i in range(len(masked_array))]) for j in range(len(masked_array[0]))])
        good_rows = np.where(nan_counts == 0)[0]
        scan_tensor = np.array([[scan_tensor_uncropped[channel, 0, good_rows], scan_tensor_uncropped[channel, 1, good_rows]] for channel in range(len(channels))])
        
        pixels = np.shape(scan_tensor[0, 0]) # The number of pixels is recalculated on the basis of the scans potentially being cropped
        scan_range = np.array([scan_range_uncropped[0], scan_range_uncropped[1] * pixels[1] / pixels_uncropped[1]]) # Recalculate the size of the slow scan direction after cropping
        scan_range_nm = scan_range * 1E9 # Return the scan range in nanometer
        
        z_controller = scan_header.get("z-controller")
        feedback = bool(z_controller.get("on", 0)[0])
        setpoint_str = z_controller.get("Setpoint", 0)[0]
        setpoint_pA = float(setpoint_str.split()[0]) * 1E12
        bias = scan_data.header.get("bias", 0)

        setattr(scan_data, "channels", channels) # Add new attributes to the nap.Scan object
        setattr(scan_data, "scan_tensor_uncropped", scan_tensor_uncropped)
        setattr(scan_data, "pixels_uncropped", pixels_uncropped)
        setattr(scan_data, "scan_range_uncropped", scan_range_uncropped)
        setattr(scan_data, "scan_tensor", scan_tensor)
        setattr(scan_data, "pixels", pixels)
        setattr(scan_data, "scan_range", scan_range)
        setattr(scan_data, "scan_range_nm", scan_range_nm)
        setattr(scan_data, "feedback", feedback)
        setattr(scan_data, "setpoint_pA", setpoint_pA)
        setattr(scan_data, "bias", bias)

        return scan_data

def image_gradient(image):
    sobel_x = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    sobel_y = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]
    ddx = convolve2d(image, sobel_x, mode = "valid")
    ddy = convolve2d(image, sobel_y, mode = "valid")
    gradient_image = .125 * ddx + .125 * 1j * ddy

    return gradient_image

def background_subtract(image, mode: str = "plane"):
    avg_image = np.mean(image.flatten()) # The average value of the image, or the offset
    gradient_image = image_gradient(image) # The (complex) gradient of the image
    avg_gradient = np.mean(gradient_image.flatten()) # The average value of the gradient

    pix_y, pix_x = np.shape(image)
    x_values = np.arange(-(pix_x - 1) / 2, pix_x / 2, 1)
    y_values = np.arange(-(pix_y - 1) / 2, pix_y / 2, 1)

    plane = np.array([[-x * np.real(avg_gradient) - y * np.imag(avg_gradient) for x in x_values] for y in y_values])

    if mode == "plane":
        return image - plane - avg_image
    elif mode == "average":
        return image - avg_image
    else:
        return image