# face-recog

###### To extract embeddings from all images in the dataset:
```
python extract_embeddings.py --dataset dataset \
	--embeddings output/embeddings.pickle \
	--detector face_detection_model \
	--embedding-model openface_nn4.small2.v1.t7
```

###### Train a face recognition model on top of the embeddings:
```
python train_model.py --embeddings output/embeddings.pickle \
	--recognizer output/recognizer.pickle \
	--le output/le.pickle
```

###### Execute Face recognition with a live video stream:
```
python recognize_video.py --detector face_detection_model \
	--embedding-model openface_nn4.small2.v1.t7 \
	--recognizer output/recognizer.pickle \
	--le output/le.pickle
```

Full docs @ [pyimagesearch] (https://www.pyimagesearch.com/2018/09/24/opencv-face-recognition/)