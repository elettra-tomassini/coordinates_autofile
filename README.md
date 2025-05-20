# coordinate_autofile

This python script was made to create a intercative videoplayer which takes input from the keyboard and creates csv files named as the key pressed. Pressing shift saves the frame and the x, y cooridnates to the selected csv file.
> Inspired by [keypoint_tracking](https://github.com/ababino/keypoint_tracking) 

## Install and Use
To use this python script you need to install:
- Anaconda
Then proceed to install the dependencies specified in ```environment.yml```

```bash
git clone https://github.com/elettra-tomassini/coordinates_autofile
cd coordinates_autofile
conda env create -f environment.yml
conda activate orcas
python coordinates_autofile /filepath
