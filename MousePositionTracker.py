import pickle
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk
from tkinter import Button
import pandas as pd
from tkinter import filedialog
import cv2 # Not directly used in the provided snippets, but kept as it's in the original imports.
import os
import numpy as np
import random
import glob
import json
from tkinter import simpledialog
from SelectionObject import SelectionObject

class MousePositionTracker(tk.Frame):
    """Tkinter Canvas mouse position tracker and ROI management widget."""
    
    def __init__(self, canvas, imwidth, imheight, text, my_imo, fps, shape_type_var=None, selection_obj=None):
        self.text = text
        self.fps = fps
        self.canvas = canvas
        self.shape_type_var = shape_type_var
        self.selection_obj = selection_obj
        self.reset()
        
        # Initialize canvas dimensions and cross-hair lines if a canvas is provided.
        if self.canvas is not None:
            self.canv_width = self.canvas.cget('width')
            self.canv_height = self.canvas.cget('height')
            xhair_opts = dict(dash=(3, 2), fill='white', state=tk.HIDDEN)
            self.lines = (self.canvas.create_line(0, 0, 0, self.canv_height, **xhair_opts),
                          self.canvas.create_line(0, 0, self.canv_width,  0, **xhair_opts))
        else:
            # Handle cases where MousePositionTracker might be instantiated without a canvas
            # (e.g., for batch processing where GUI elements are not needed).
            self.canv_width = None
            self.canv_height = None
            self.lines = (None, None)

        self.im_height = imheight
        self.im_width = imwidth
        self.my_imo = my_imo
        self.im_list = [] # Stores PhotoImage objects to prevent garbage collection
        self.SELECT_OPTS = dict(dash=(2, 2), stipple='gray25', fill='red',
                          outline='')
        self.is_dragging = False # Flag to track mouse drag state
   
    def cur_selection(self):
        """Returns the start and end coordinates of the current selection."""
        return (self.start, self.end)

    def track(self):
        """Re-initializes the mouse position tracker."""
        # Note: In the original code, this also re-initialized SelectionObject.
        # In the refactored code, SelectionObject is passed via __init__ and managed externally.
        self.posn_tracker = MousePositionTracker(self.canvas,  self.im_width, self.im_height,self.text,self.my_imo, self.fps)

    def begin(self, event):
        """Starts a new selection by recording the initial mouse position."""
        self.hide()
        self.reset() # Reset previous selection
        if self.selection_obj:
            self.selection_obj.reset_shape() # Clear any active interactive selection shape
        self.start = (event.x, event.y)
        self.top_left_X = event.x
        self.top_left_Y = event.y
        # Scale coordinates to original image dimensions (assuming canvas is 640x420)
        self.TLX = self.top_left_X * (self.im_width / 640)
        self.TLY = self.top_left_Y * (self.im_height / 420)
        self.is_dragging = True

    def endclick(self, event):
        """Records the final mouse position upon button release."""
        self.hide()
        self.bottom_right_X = event.x
        self.bottom_right_Y = event.y
        # Scale coordinates to original image dimensions
        self.BRX = self.bottom_right_X * (self.im_width / 640)
        self.BRY = self.bottom_right_Y * (self.im_height / 420)

    def update(self, event):
        """Updates the interactive selection shape and cross-hairs during a drag."""
        self.end = (event.x, event.y)
        self._update(event)
        self._command(self.start, (event.x, event.y)) # User callback for selection updates

    def _update(self, event):
        """Internal method to update cross-hair lines."""
        self.canvas.coords(self.lines[0], event.x, 0, event.x, self.canv_height)
        self.canvas.coords(self.lines[1], 0, event.y, self.canv_width, event.y)
        self.show()

    def reset(self):
        """Resets the stored start and end coordinates."""
        self.start = self.end = None

    def hide(self):
        """Hides the cross-hair lines."""
        self.canvas.itemconfigure(self.lines[0], state=tk.HIDDEN)
        self.canvas.itemconfigure(self.lines[1], state=tk.HIDDEN)

    def show(self):
        """Shows the cross-hair lines."""
        self.canvas.itemconfigure(self.lines[0], state=tk.NORMAL)
        self.canvas.itemconfigure(self.lines[1], state=tk.NORMAL)

    def autodraw(self,command=lambda *args: None):
        """Sets up automatic drawing for ROI selection."""
        self.reset()
        self.ALL_ROIs=pd.DataFrame(columns=['ROI','TLX','TLY','BRX','BRY','FPS'])
        self._command = command
        self.canvas.bind("<Button-1>", self.begin)
        self.canvas.bind("<B1-Motion>", self.update)
        self.canvas.bind("<ButtonRelease-1>", self.quit)
        self.canvas.bind("<ButtonRelease-1>", self.endclick)

    def set_and_name(self):
        """Sets the selected ROI, assigns a name and color, and draws it permanently."""
        with open('COLOURS.json') as json_file:
            COLOURS = json.load(json_file)
      
        colour=random.choice(COLOURS)
        USER_INP = simpledialog.askstring(title="ROI name",
                                  prompt="ROI name:")
        if not USER_INP: # Handle case where user cancels the dialog
            self.text.insert(tk.INSERT, "\nROI naming cancelled.")
            if self.selection_obj:
                self.selection_obj.reset_shape()
            return

        self.text.insert(tk.INSERT,("\nThe ROI {} is set and coloured {}".format(USER_INP, colour)))
        
        # Get shape type from the associated Tkinter variable
        shape_type = self.shape_type_var.get() if self.shape_type_var else "Rectangle"

        # Get the current coordinates from the SelectionObject, which represents the drawn shape
        current_x1 = self.selection_obj.current_x1
        current_y1 = self.selection_obj.current_y1
        current_x2 = self.selection_obj.current_x2
        current_y2 = self.selection_obj.current_y2

        # Scale coordinates back to original image dimensions for data storage
        # Assumes 640x420 is the display canvas size.
        scaled_tlx = min(current_x1, current_x2) * (self.im_width / 640)
        scaled_tly = min(current_y1, current_y2) * (self.im_height / 420)
        scaled_brx = max(current_x1, current_x2) * (self.im_width / 640)
        scaled_bry = max(current_y1, current_y2) * (self.im_height / 420)

        # Create a DataFrame row for the new ROI, including its shape type
        Current_ROI=pd.DataFrame({'ROI':USER_INP,
                                      'TLX':scaled_tlx,
                                      'TLY':scaled_tly,
                                      'BRX':scaled_brx,
                                      'BRY':scaled_bry,
                                      'ShapeType': shape_type},index=[0])

        # Use _append for future compatibility
        self.ALL_ROIs = self.ALL_ROIs._append(Current_ROI, ignore_index=True)

        # Crop and display the image within the selected ROI
        img = ImageTk.PhotoImage(self.my_imo.crop((min(current_x1,current_x2),min(current_y1,current_y2),max(current_x1,current_x2),max(current_y1,current_y2))))
        self.im_list.append(img) # Keep a reference to prevent garbage collection
        self.image_on_canvas=self.canvas.create_image(min(current_x1,current_x2),min(current_y1,current_y2), image=img, anchor=tk.NW)

        # Draw the permanent shape on the canvas based on the selected type
        if self.canvas is not None and self.shape_type_var is not None:
            if shape_type == "Rectangle":
                shape_id = self.canvas.create_rectangle(current_x1, current_y1, current_x2, current_y2, outline=colour,width=5)
            elif shape_type == "Circle":
                # For circle, the stored coords are the bounding box of the circle
                shape_id = self.canvas.create_oval(current_x1, current_y1, current_x2, current_y2, outline=colour,width=5)

            # Bring the newly created permanent shape to the front
            self.canvas.lift(shape_id)

        # After setting and naming, reset the interactive selection object for the next draw
        if self.selection_obj:
            self.selection_obj.reset_shape()

    def _calculate_bodyparts_to_ROI_data(self):
        """
        Calculates which ROI each bodypart is in for every frame.
        This method performs the core logic without GUI interaction, making it reusable for batch processing.
        Handles both Rectangle and Circle ROI types.
        """
        # Get unique body part names from the DataFrame columns
        body_part_names = list(dict.fromkeys(self.data.columns.get_level_values(0)))

        # Extract X and Y coordinate data for all body parts
        X_data_list = [self.data[(bp_name, 'x')] for bp_name in body_part_names]
        Y_data_list = [self.data[(bp_name, 'y')] for bp_name in body_part_names]
        
        X_data = np.array(pd.concat(X_data_list, axis=1))
        Y_data = np.array(pd.concat(Y_data_list, axis=1))

        # Apply cropping parameters if the video was cropped in DLC
        if self.cropping:
            X_data += self.crop_params[0] # Add x-offset
            Y_data += self.crop_params[2] # Add y-offset

        # Initialize DataFrame to store ROI assignments for each body part
        # Initialize with "Nothing" and object dtype to allow both numbers and strings
        My_ROI_df = pd.DataFrame("Nothing", index=self.data.index, columns=body_part_names, dtype=object)

        # Iterate through each defined ROI to check body part containment
        for index, ROI in self.ALL_ROIs.iterrows():
            roi_name = ROI['ROI']
            tly = ROI['TLY']
            bry = ROI['BRY']
            tlx = ROI['TLX']
            brx = ROI['BRX']
            # Get ShapeType, defaulting to 'Rectangle' for older ROI files
            shape_type = ROI.get('ShapeType', 'Rectangle')

            truth_array = np.zeros_like(X_data, dtype=bool) # Initialize truth array for current ROI

            if shape_type == "Rectangle":
                # Check if body part coordinates are within the rectangular bounding box
                truth_array = ((Y_data > tly) & (Y_data < bry) & (X_data > tlx) & (X_data < brx))

            elif shape_type == "Circle":
                # Calculate center and radius from the bounding box for a circle
                center_x = (tlx + brx) / 2
                center_y = (tly + bry) / 2
                radius = (brx - tlx) / 2 # Assumes bounding box is square for a circle

                # Calculate Euclidean distance from the circle's center for all body parts
                distance_from_center = np.sqrt((X_data - center_x)**2 + (Y_data - center_y)**2)

                # Check if distance is within the radius
                truth_array = (distance_from_center <= radius)

            else:
                print(f"Warning: Unknown shape type '{shape_type}' for ROI '{roi_name}'. Skipping analysis for this ROI.")
            
            # Assign the ROI name to body parts that fall within this ROI
            # Use .loc for boolean indexing and assignment
            for i, col_name in enumerate(body_part_names):
                 My_ROI_df.loc[truth_array[:, i], col_name] = roi_name

        # Determine the majority ROI for each frame across all body parts
        My_ROI_df['Majority'] = My_ROI_df.mode(axis=1).iloc[:,0]

        # Calculate entries into regions
        # Shift region names down one value and check difference to original region names
        entries = (My_ROI_df.Majority.ne(My_ROI_df.Majority.shift())).astype(int)
        entries.iloc[0] = 0 # Set first entry to zero as it's not a region entry from a previous one

        # Multiply region entries by ROI names to get the region being entered
        # Ensure My_ROI_df.Majority is string for multiplication if entries is 1
        My_ROI_df['entries'] = (entries * My_ROI_df.Majority.astype(str)).astype(str)
        
        # Determine the region entered from
        My_ROI_df['enteredFrom'] = My_ROI_df['entries'] + ' from ' + My_ROI_df['Majority'].shift().astype(str)
        My_ROI_df['enteredFrom'] *= entries # Keep only entries where an actual entry occurred
        My_ROI_df.fillna('', inplace=True) # Fill NaN values, typically from shift(), with empty strings

        return My_ROI_df

    def bodyparts_to_ROI(self):
        """
        Calculates which ROI each bodypart is in and saves the result to a CSV file.
        This method is typically called from the GUI after ROI definition.
        """
        self.bp_data = self._calculate_bodyparts_to_ROI_data()

        self.save_path = simpledialog.askstring(title="Save bodypart data",
                                  prompt="File name:")
        
        # Check if the user provided a file name (i.e., did not cancel the dialog)
        if self.save_path:
            self.bp_data.to_csv(self.save_path + ".csv")
            self.text.insert(tk.INSERT, f"\nBody part ROI data saved to {self.save_path}.csv")
        else:
            self.text.insert(tk.INSERT, "\nSaving cancelled by user.")

    def read_pickle(self, filename):
        """Reads a pickle file and returns its content."""
        with open(filename, "rb") as handle:
            return pickle.load(handle)

    def load_video_metadata(self, file):
        """
        Loads metadata (e.g., cropping parameters) associated with a video file.
        Looks for a .pickle file with the same base name as the video.
        """
        metadata_path = os.path.splitext(file)[0]
        metadata_files = glob.glob(f"{metadata_path}*.pickle")
        if not metadata_files:
            # Removed self.text.insert here to prevent GUI pop-ups during batch processing.
            return None
        metadata = self.read_pickle(metadata_files[0])
        return metadata

    def load_deeplab_Coords(self):
        """
        Loads DeepLabCut (DLC) tracking coordinates from a .h5 or .csv file.
        Also attempts to load associated video metadata for cropping information.
        """
        path = filedialog.askopenfilename(filetypes = ([("h5 and csv files",".h5 .csv")]))
        if not path: # Handle case where user cancels file dialog
            self.text.insert(tk.INSERT, "\nDLC file loading cancelled.")
            return

        if path.endswith('.h5'):
            self.data = pd.read_hdf(path)
        else:
            self.data = pd.read_csv(path, header=[0,1,2])
        
        # Drop the top level (scorer) from multi-index columns
        self.data.columns = self.data.columns.droplevel(0)
        # Drop 'likelihood' columns from the second level after droplevel(0)
        self.data = self.data.drop('likelihood', axis=1, level=1)

        metadata = self.load_video_metadata(path)
        if metadata is None:
            self.cropping = False
            self.text.insert(tk.INSERT,
                            "\n\nNo pickle file found for this video. Cropping information might be missing.\n\n")
            return
        
        self.cropping = metadata["data"]["cropping"]
        self.crop_params = metadata["data"]["cropping_parameters"]
        self.text.insert(tk.INSERT, f"\nLoaded DLC data from {os.path.basename(path)}.")
        if self.cropping:
            self.text.insert(tk.INSERT, f"\nVideo was cropped with parameters: {self.crop_params}")


    def load_ROI_file(self):
        """Loads previously saved ROI definitions from a CSV file."""
        path = filedialog.askopenfilename()
        if not path: # Handle case where user cancels file dialog
            self.text.insert(tk.INSERT, "\nROI file loading cancelled.")
            return
        self.ALL_ROIs = pd.read_csv(path)
        # Assuming FPS is stored in the first row of the 'FPS' column
        if 'FPS' in self.ALL_ROIs.columns:
            self.fps = self.ALL_ROIs['FPS'][0]
        else:
            self.text.insert(tk.INSERT, "\n'FPS' column not found in ROI file. Please set FPS manually if needed.")
            # Default FPS to a common value or prompt user if critical
            self.fps = 30 # Default value if not found
        self.text.insert(tk.INSERT, f"\nLoaded ROI definitions from {os.path.basename(path)}. FPS set to {self.fps}.")

    def Analyse_ROI(self):        
        """Placeholder for further ROI analysis. Currently calculates value counts."""
        counts=self.bp_data['Majority'].value_counts().to_dict()
        # Further analysis logic would go here.
        
    def quit(self, event):
        """Hides cross-hairs and resets selection on button release."""
        self.hide()
        self.reset()
        self.is_dragging = False # Reset drag state

    def save_All_ROIs(self):
        """Saves all defined ROIs to a CSV file."""
        USER_INP = simpledialog.askstring(title="File name",
                                  prompt="ROI File name:")
        if not USER_INP: # Handle case where user cancels the dialog
            self.text.insert(tk.INSERT, "\nSaving ROI file cancelled.")
            return

        self.ALL_ROIs['FPS'] = self.fps # Ensure FPS is saved with ROIs
        self.ALL_ROIs.to_csv(USER_INP + ".csv", index=False) # index=False to prevent writing DataFrame index
        self.text.insert(tk.INSERT, f"\nSaved ROIs as {USER_INP}.csv")

    def process_batch(self, batch_file_path):
        """
        Processes multiple DLC data files and ROI definitions from a batch CSV file.
        The batch CSV should have two columns: 'ROI_File_Path' and 'DLC_File_Path'.
        Results are saved to 'output.csv'.
        """
        try:
            batch_df = pd.read_csv(batch_file_path)
        except Exception as e:
            self.text.insert(tk.INSERT, f"\nError reading batch file {batch_file_path}: {e}")
            return

        results = []

        for index, row in batch_df.iterrows():
            shape_file = row[0] # Assuming first column is ROI file path
            h5_file = row[1]    # Assuming second column is DLC file path
            
            self.text.insert(tk.INSERT, f"\nProcessing: ROI='{os.path.basename(shape_file)}', DLC='{os.path.basename(h5_file)}'")

            try:
                # Load ROI data
                self.ALL_ROIs = pd.read_csv(shape_file)
                # Set FPS from the ROI file; assume it's in the first row
                if 'FPS' in self.ALL_ROIs.columns:
                    self.fps = self.ALL_ROIs['FPS'][0]
                else:
                    self.fps = 30 # Default if FPS column is missing
                    self.text.insert(tk.INSERT, "\nWarning: 'FPS' column not found in ROI file. Defaulting to 30 FPS.")

                # Load DLC data
                if h5_file.endswith('.h5'):
                    self.data = pd.read_hdf(h5_file)
                else:
                    self.data = pd.read_csv(h5_file, header=[0, 1, 2])
                
                # Clean DLC data columns
                self.data.columns = self.data.columns.droplevel(0) # Drop scorer level
                self.data = self.data.drop('likelihood', axis=1, level=1) # Drop likelihood

                # Load metadata for cropping if available
                metadata = self.load_video_metadata(h5_file)
                self.cropping = False # Default to no cropping
                if metadata:
                    self.cropping = metadata["data"]["cropping"]
                    self.crop_params = metadata["data"]["cropping_parameters"]
                else:
                    self.text.insert(tk.INSERT, "\nNo pickle metadata found for DLC file. Cropping will not be applied.")

                # Perform analysis using the dedicated analysis method
                analysis_result = self.analyze_data()

                # Store results, including the filename for identification
                result_row = {'h5_file': os.path.basename(h5_file)}
                result_row.update(analysis_result)
                results.append(result_row)

            except Exception as e:
                self.text.insert(tk.INSERT, f"\nError processing {os.path.basename(h5_file)} with {os.path.basename(shape_file)}: {e}")
                results.append({'h5_file': os.path.basename(h5_file), 'error': str(e)})

        # Write all collected results to a single output CSV file
        if results:
            output_df = pd.DataFrame(results)
            output_df.to_csv("output.csv", index=False)
            self.text.insert(tk.INSERT, "\nBatch processing complete. Results saved to output.csv")
        else:
            self.text.insert(tk.INSERT, "\nBatch processing completed, but no results were generated.")

    def analyze_data(self):
        """
        Analyzes time spent and entries for the loaded DLC data based on defined ROIs.
        This method encapsulates the analysis logic for both single-file and batch processing.
        """
        analysis_results = {}

        # Calculate body part ROI assignments
        self.bp_data = self._calculate_bodyparts_to_ROI_data()

        # Define the full data range for analysis
        start_frame = 0
        end_frame = self.data.shape[0]

        # Calculate entries into regions (logic reused from detect_entries)
        entries = (self.bp_data.Majority.ne(self.bp_data.Majority.shift())).astype(int)
        entries.iloc[0] = 0 # First entry is not a transition
        self.bp_data['entries'] = (entries * self.bp_data.Majority.astype(str)).astype(str)
        self.bp_data['enteredFrom'] = self.bp_data['entries'] + ' from ' + self.bp_data['Majority'].shift().astype(str)
        self.bp_data['enteredFrom'] *= entries
        self.bp_data.fillna('', inplace=True)

        # Count entries
        entry_dict = self.bp_data['entries'][start_frame:end_frame].value_counts().to_dict()
        if '' in entry_dict: # Remove empty string entries (non-transitions)
            entry_dict.pop('')

        for entry in entry_dict:
            analysis_results[entry + " entries"] = entry_dict[entry]

        # Count entries from specific regions
        entry_from_dict = self.bp_data['enteredFrom'][start_frame:end_frame].value_counts().to_dict()
        if '' in entry_from_dict:
            entry_from_dict.pop('')
        
        for entryfrom in entry_from_dict:
            analysis_results[entryfrom] = entry_from_dict[entryfrom]

        # Calculate time spent in each ROI
        time_spent_dict = self.bp_data.Majority[start_frame:end_frame].value_counts().to_dict()
        for roi in time_spent_dict:
            # Convert frame count to seconds
            secs_spent = int(time_spent_dict[roi]) / self.fps
            analysis_results[roi + " time spent"] = secs_spent

        return analysis_results

    def detect_entries(self):
        """
        Prompts user for time range and calculates ROI entries and time spent,
        displaying results in the text output and saving to CSV.
        This method is for interactive GUI use.
        """
        start_time_sec = simpledialog.askinteger(title="Start time in seconds",
                                  prompt="Start(s):")
        end_time_sec = simpledialog.askinteger(title="End time in seconds",
                                  prompt="End(s):")
        # 'bucket_len' parameter is not used in the current implementation, but kept for compatibility.
        bucket_len_sec = simpledialog.askinteger(title="Length of buckets in seconds",
                          prompt="bucket length(s):")

        if start_time_sec is None or end_time_sec is None: # User cancelled
            self.text.insert(tk.INSERT, "\nAnalysis cancelled by user.")
            return

        # Convert time in seconds to frame indices
        start_frame = int(start_time_sec * self.fps)
        end_frame = int(end_time_sec * self.fps)

        # Ensure bp_data is calculated before proceeding
        if not hasattr(self, 'bp_data') or self.bp_data is None:
            self.text.insert(tk.INSERT, "\nDLC data not loaded or ROIs not analyzed. Please load DLC data and run 'Bodyparts to ROI' first.")
            return

        # The core analysis logic is now in analyze_data, but detect_entries has GUI output
        # Re-apply entry/enteredFrom calculation for the specific time window
        entries = (self.bp_data.Majority.ne(self.bp_data.Majority.shift())).astype(int)
        entries.iloc[0] = 0
        self.bp_data['entries'] = (entries * self.bp_data.Majority.astype(str)).astype(str)
        self.bp_data['enteredFrom'] = self.bp_data['entries'] + ' from ' + self.bp_data['Majority'].shift().astype(str)
        self.bp_data['enteredFrom'] *= entries
        self.bp_data.fillna('', inplace=True)

        data_analysis = pd.DataFrame()

        # Calculate and display entries
        entry_dict = self.bp_data['entries'][start_frame:end_frame].value_counts().to_dict()
        if '' in entry_dict:
            entry_dict.pop('')

        for entry in entry_dict:
            self.text.insert(tk.INSERT, f"\nAnimal entered {entry} {entry_dict[entry]} times")
            data_analysis[entry + " entries"] = pd.DataFrame({entry + " entries": entry_dict[entry]}, index=[0])
          
        # Calculate and display entries from specific regions
        entry_from_dict = self.bp_data['enteredFrom'][start_frame:end_frame].value_counts().to_dict()
        if '' in entry_from_dict:
            entry_from_dict.pop('')

        for entryfrom in entry_from_dict:
            self.text.insert(tk.INSERT, f"\nAnimal entered {entryfrom} {entry_from_dict[entryfrom]} times")
            data_analysis[entryfrom] = pd.DataFrame({entryfrom: entry_from_dict[entryfrom]}, index=[0])
          
        # Calculate and display time spent in each ROI
        time_spent_dict = self.bp_data.Majority[start_frame:end_frame].value_counts().to_dict()
        for roi in time_spent_dict:
            secs_spent = int(time_spent_dict[roi]) / self.fps
            self.text.insert(tk.INSERT, f"\nTime spent in {roi} is {secs_spent:.2f} seconds")
            data_analysis[roi + " time spent"] = pd.DataFrame({roi + " time spent": secs_spent}, index=[0])
        
        # Add a BIN column for consistency if needed, though only one row for total time
        data_analysis.insert(0, 'BIN', "total_time") 
        
        # Save analysis results to CSV
        if hasattr(self, 'save_path') and self.save_path:
            data_analysis.to_csv(self.save_path + 'entries_and_time_spent.csv', index=False)
            self.text.insert(tk.INSERT, f"\nAnalysis saved to {self.save_path}entries_and_time_spent.csv")
        else:
            self.text.insert(tk.INSERT, "\nNo save path set. Analysis results not saved to file.")
