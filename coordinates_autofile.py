import argparse
import csv
import logging
import os
import wx
import numpy
from skvideo.io import ffprobe, FFmpegReader
import cv2  # Ensure OpenCV is installed

# Fix numpy deprecation warnings
numpy.float = numpy.float64
numpy.int = numpy.int_


def array_to_wx(image):
    """Convert a numpy array to a wx.Bitmap."""
    height, width = image.shape[:-1]
    buffer = image.tobytes()
    bitmap = wx.Bitmap.FromBuffer(width, height, buffer)
    return bitmap


class Panel(wx.Panel):
    def __init__(self, parent, video, frame_rate, frame_shape):
        super(Panel, self).__init__(parent, -1)
        self.video = video
        self.parent = parent
        self.fr = frame_rate  # Frame rate
        self.frame_shape = frame_shape  # Video frame dimensions

        # Set panel size
        screen_width, screen_height = wx.GetDisplaySize()
        self.SetSize((screen_width, screen_height))
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)

        # Initialize variables
        self.pos = None
        self.frame_n = None
        self.play = False
        self.exit = False
        self.breath = 0
        self.annotation = {}
        self.current_output_file = None  # Current output file
        self.fieldnames = ['frame', 'x', 'y', 'breath']

        # Bind events
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_MOTION, self.store_pos)
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)

        # Start the update loop
        self.update()

    def update(self):
        """Update the panel and handle playback."""
        if self.exit:
            return  # Exit early if the panel has been marked for closing

        if self.play:
            self.Refresh()
            self.Update()

        if not self.exit:
            wx.CallLater(1, self.update)

    def create_bitmap(self):
        """Create a wx.Bitmap from the current video frame."""
        try:
            self.frame_n, frame = self.video.__next__()
        except StopIteration:
            return None

        # Get screen size
        screen_width, screen_height = wx.GetDisplaySize()

        # Get original video dimensions
        vid_height, vid_width = self.frame_shape[:2]

        # Calculate scaling factor to fit video on screen
        scale_w = screen_width / vid_width
        scale_h = screen_height / vid_height
        scale = min(scale_w, scale_h, 1)  # Only scale down, not up

        # Resize frame if necessary
        if scale < 1:
            new_width = int(vid_width * scale)
            new_height = int(vid_height * scale)
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        bitmap = array_to_wx(frame)
        return bitmap

    def on_paint(self, event):
        """Handle the paint event to draw the video frame and overlay the time."""
        bitmap = self.create_bitmap()
        if bitmap is None:
            return

        # Calculate the current time in seconds
        if self.frame_n is not None:
            current_time = self.frame_n / self.fr  # 'fr' is the frame rate
        else:
            current_time = 0

        # Format the time as MM:SS
        minutes = int(current_time // 60)
        seconds = int(current_time % 60)
        time_text = f"{minutes:02}:{seconds:02}"

        # Draw the video frame
        dc = wx.AutoBufferedPaintDC(self)
        dc.DrawBitmap(bitmap, 0, 0)

        # Overlay the time on the video
        dc.SetTextForeground(wx.Colour(255, 255, 255))  # White text
        dc.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        dc.DrawText(time_text, 10, 10)  # Position the text at the top-left corner

    def store_pos(self, event):
        """Store the mouse position scaled to the original video dimensions."""
        pos = event.GetPosition()

        # Get screen size
        screen_width, screen_height = wx.GetDisplaySize()

        # Get original video dimensions
        vid_height, vid_width = self.frame_shape[:2]

        # Calculate scaling factor
        scale_w = screen_width / vid_width
        scale_h = screen_height / vid_height
        scale = min(scale_w, scale_h, 1)

        # Scale the recorded position back to the original dimensions
        self.pos = {
            'x': int(pos[0] / scale),
            'y': int(pos[1] / scale)
        }

    def onKeyPress(self, event):
        """Handle key press events."""
        keycode = event.GetKeyCode()

        # Check if the key is a letter (A-Z or a-z)
        if 65 <= keycode <= 90 or 97 <= keycode <= 122:
            letter = chr(keycode).lower()  # Convert to lowercase
            self.current_output_file = f"{letter}.csv"

            # Check if the file already exists
            if not os.path.exists(self.current_output_file):
                # If the file doesn't exist, create it and write the header
                with open(self.current_output_file, 'w') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writeheader()
                logging.info(f"Created new output file: {self.current_output_file}")
            else:
                logging.info(f"Switched to existing output file: {self.current_output_file}")

        elif keycode == wx.WXK_SHIFT:
            self.breath = 1

            # Save the current frame and position
            if self.pos and self.current_output_file:
                with open(self.current_output_file, 'a') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writerow({'frame': self.frame_n, 'x': self.pos['x'], 'y': self.pos['y'], 'breath': self.breath})
                    logging.debug('Saved frame %s: x=%s, y=%s, breath=%s to %s', self.frame_n, self.pos['x'], self.pos['y'], self.breath, self.current_output_file)

        elif keycode == wx.WXK_SPACE:
            self.play = not self.play
        elif keycode == wx.WXK_ESCAPE:
            self.exit = True
            logging.debug('escape %s', self.exit)
            self.Close()
            self.parent.Close()


class Frame(wx.Frame):
    def __init__(self, video, frame_rate, frame_shape):
        style = wx.DEFAULT_FRAME_STYLE & ~wx.RESIZE_BORDER & ~wx.MAXIMIZE_BOX
        super(Frame, self).__init__(None, -1, 'Camera Viewer', style=style)

        # Get display size AFTER wx.App is created
        screen_width, screen_height = wx.GetDisplaySize()

        # Set frame to match display size
        self.SetSize((screen_width, screen_height))

        # Center panel inside the frame
        panel = Panel(self, video, frame_rate, frame_shape)
        panel.Centre()  # Optional: you can use a sizer instead for better control


def main(video, frame_rate, frame_shape):
    """Main function to initialize the wx.App and start the GUI."""
    app = wx.App()  # Initialize wx.App
    frame = Frame(video, frame_rate, frame_shape)  # Create the main frame
    frame.Center()
    frame.Show()
    app.MainLoop()  # Start the event loop


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("file_path", help="path to the video.")
    parser.add_argument("--skip", type=float, default=0,
                        help="seconds to skip at the beginning of the video. Default 0.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG)
    file_path = args.file_path

    metadata = ffprobe(file_path)['video']
    fr = float(metadata['@r_frame_rate'].split('/')[0]) / float(metadata['@r_frame_rate'].split('/')[1])
    frame_shape = (int(metadata['@height']), int(metadata['@width']), 3)
    skip = args.skip

    # Print the video frame dimensions
    print(f"Video frame dimensions: width={frame_shape[1]}, height={frame_shape[0]}")

    secs = skip / fr
    video = enumerate(FFmpegReader(file_path, inputdict={'-ss': str(secs)}), skip)

    main(video, fr, frame_shape)