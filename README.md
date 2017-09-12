# Generates a dataset from internet archive audio files to be processed by a binary classifer
Generates a dataset from internet archive audio files to be processed by a binary classifer.

# How
Uses the internetarchive Python library to access the internet archive and download a set audio files that will be used for training.
It then pre-process the audio files and outputs usable files usable by a Machine Learning Model

# What do we want the algorithm to learn here?
We want the model to learn the sound of human Speech in isolation. We don't want human speech + music, human speech + background noise (like sounds from things, animals, natural sounds, environment, etc), just music or just background noise.

We want our model to output 1 for clean human Speech and 0 for everything else. We consider echo and distorsion from low quality recordings or low quality encoding to be also "non-clean speech".


# What is the dataset set composed of?
The dataset is composed of internetarchive audio files. Files from the Librivox catalog are used as the "clean speech training examples". To slightly enforce better quality

To generate the "non-clean training examples" Audio files from these categories are used:
- music
- instrumental
- 78rpm
- ambient
- noise
- drone

Additonally, data is augmented by taking the Librivox speech files and combining them with the other audio files to produce additional "non-clean examples".

# What are the limitations of this approach?
## The dataset does not take into account the differences


