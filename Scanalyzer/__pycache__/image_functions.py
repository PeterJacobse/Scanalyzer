import os
import numpy as np
import nanonispy2 as nap

def get_scan(file_name, crop_unfinished: bool = True):
    if not os.path.exists(file_name):
        print(f"Error: File \"{file_name}\" does not exist.")
        return
    else:
        scan_data = nap.read.Scan(file_name) # Read the scan data
        channels = np.array([key for key in scan_data.signals.keys()])
        scans = [scan_data.signals[key] for key in channels]
        scan_header = scan_data.header
        header_keys = [key for key in scan_header.keys()]
        header_values = [scan_header[key] for key in header_keys]
        up_or_down = scan_header.get("scan_dir", "down")
        
        # Stack the forward and backward scans for each channel in a big tensor. Flip the backward scan
        all_scans = np.stack([np.stack((np.array(scan_data.signals[channel]["forward"], dtype = float), np.flip(np.array(scan_data.signals[channel]["backward"], dtype = float), axis = 1))) for channel in channels])
        if up_or_down == "up": all_scans = np.flip(all_scans, axis = 2) # Flip the scan if it recorded down to up

        if crop_unfinished:
            # Determine which rows should be cropped off in an uncompleted scan
            masked_array = np.isnan(all_scans[0, 1]) # The backward scan has more NaN values because the scan always starts in the forward direction
            nan_counts = np.array([sum([int(masked_array[j, i]) for i in range(len(masked_array))]) for j in range(len(masked_array[0]))])
            good_rows = np.where(nan_counts == 0)[0]
            all_scans_processed = np.array([[all_scans[channel, 0, good_rows], all_scans[channel, 1, good_rows]] for channel in range(len(channels))])
        else: all_scans_processed = all_scans

        angle = float(scan_header.get("scan_angle", 0))
        pixels = np.shape(all_scans_processed[0, 0])
        date = scan_header.get("rec_date", "00.00.1900")
        time = scan_header.get("rec_time", "00:00:00")
        center = scan_header.get("scan_offset", np.array([0, 0], dtype = float))
        size = scan_header.get("scan_range", np.array([1E-7, 1E-7], dtype = float))
        bias = scan_data.header.get("bias", 0)

        return all_scans_processed