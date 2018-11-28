from __future__ import division
import numpy as np
import os
import six.moves.urllib as urllib
import sys
import tarfile
import tensorflow as tf
import zipfile
from collections import defaultdict
from io import StringIO
from PIL import Image
import cv2
import argparse
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
CWD_PATH = os.getcwd()

import detect_color as detect_color
import get_info as get_info
#colors to detect as shirts supported
colors=['red','yellow','green','blue']

NUM_CLASSES = 90

#classe 1 person class 37 sports ball
PERSON = 1
SPORTS_BALL = 37
THRESHOLD = 0.40
TEAM_1 = 1
TEAM_2 = 2
# This is needed since the notebook is stored in the object_detection folder.
sys.path.append("..")

# Path to frozen detection graph. This is the actual model that is used for the object detection.
# Note: Model used for SSDLite_Mobilenet_v2
MODEL_NAME = 'ssd_mobilenet_v1_coco_11_06_2017'
PATH_TO_CKPT = os.path.join(CWD_PATH, 'object_detection', MODEL_NAME, 'frozen_inference_graph.pb')
# List of the strings that is used to add correct label for each box.
PATH_TO_LABELS = os.path.join(CWD_PATH, 'object_detection', 'data', 'mscoco_label_map.pbtxt')




class soccer_game:
    def __init__(self):
        self.team1 = get_info.get_name(TEAM_1)
        self.color1 = get_info.get_color(TEAM_1,colors)
        self.team2 = get_info.get_name(TEAM_2)
        self.color2 = get_info.get_color(TEAM_2,colors)
    
    def print_info(self):
        print("Teams information\n")
        print("Team number 1 name :\n",self.team1)
        print("Team number 1 colors :\n",self.color1)
        print("Team number 2 name :\n",self.team2)
        print("Team number 2 colors :\n",self.color2)

    def set_video_output(self,input_name,output_name):
        filename = get_info.get_video_file(input_name)
        cap = cv2.VideoCapture(filename)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        fourcc = cv2.VideoWriter_fourcc('m','p','4','v') # note the lower case
        out = cv2.VideoWriter(output_name, fourcc, fps, (width, height))
        return cap, out, width, height


def main():
    #parse arguments
    parser=argparse.ArgumentParser()
    parser.add_argument('-i','--input',required=True)
    parser.add_argument('-o','--output',required=True)
    args = parser.parse_args()
    
    #get teams names and colors
    soccer_game_curr = soccer_game()
    soccer_game_curr.print_info()
    color1 = soccer_game_curr.color1
    color2 = soccer_game_curr.color2
    team1 = soccer_game_curr.team1
    team2 = soccer_game_curr.team2

    #intializing the input and output video
    [cap, out, width, height] = soccer_game_curr.set_video_output(args.input, args.output)

    #set tf graph
    detection_graph = tf.Graph()
    with detection_graph.as_default():
      od_graph_def = tf.GraphDef()
      with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')

    label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES, use_display_name=True)

    category_index = label_map_util.create_category_index(categories)


    # Running the tensorflow session
    with detection_graph.as_default():
        with tf.Session(graph=detection_graph) as sess:
            counter = 0
            print("--------------------------Start tracking video--------------------------\n")
            while(True):

                ret, image_np = cap.read()
                counter += 1
                if ret:
                    h = image_np.shape[0]
                    w = image_np.shape[1]

                if not ret:
                    break
                if counter % 1 == 0:

                    # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
                    image_np_expanded = np.expand_dims(image_np, axis=0)
                    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')

                    # Each box represents a part of the image where a particular object was detected.
                    boxes = detection_graph.get_tensor_by_name('detection_boxes:0')

                    # Each score represent how level of confidence for each of the objects.
                    # Score is shown on the result image, together with the class label.
                    scores = detection_graph.get_tensor_by_name('detection_scores:0')
                    classes = detection_graph.get_tensor_by_name('detection_classes:0')
                    num_detections = detection_graph.get_tensor_by_name('num_detections:0')

                    # Actual detection.
                    (boxes, scores, classes, num_detections) = sess.run(
                        [boxes, scores, classes, num_detections],
                        feed_dict={image_tensor: image_np_expanded})

                    class_to_delete = []
                    for i, x in np.ndenumerate(classes):
                        if (x!=PERSON and x!=SPORTS_BALL):
                            class_to_delete.append(i[1])
                    classes = np.delete(classes,class_to_delete,1)
                    scores = np.delete(scores,class_to_delete,1)
                    boxes = np.delete(boxes,class_to_delete,1)

                    # Visualization of the results of a detection.
                    vis_util.visualize_boxes_and_labels_on_image_array(
                        image_np,
                        np.squeeze(boxes),
                        np.squeeze(classes).astype(np.int32),
                        np.squeeze(scores),
                        category_index,
                        use_normalized_coordinates=True,
                        line_thickness=3,
                        min_score_thresh=0.3)
                    frame_number = counter
                    loc = {}

                    all_xmin = []
                    all_xmax = []

                    for n in range(len(scores[0])):
                        if scores[0][n] > THRESHOLD:
                            # Calculate position
                            ymin = int(boxes[0][n][0] * h)
                            xmin = int(boxes[0][n][1] * w)
                            ymax = int(boxes[0][n][2] * h)
                            xmax = int(boxes[0][n][3] * w)

                            if (xmax-xmin) < 0.5*width and (ymax-ymin) < 0.5*height:

                                all_xmax.append(xmax)
                                all_xmin.append(xmin)

                                # Find label corresponding to that class
                                for cat in categories:
                                    if cat['id'] == classes[0][n]:
                                        label = cat['name']

                                ## extract every person
                                if label == 'person':
                                    #crop them
                                    crop_img = image_np[ymin:ymax, xmin:xmax]
                                    color = detect_color.detect_team(crop_img,color1,color2)

                                    #if color != 'not_sure':
                                    coords = (xmin, ymin)
                                    if color == color1:
                                        loc[coords] = team1
                                    elif color==color2:
                                        loc[coords] = team2
                                    else:
                                        loc[coords]='UNKNOWN TEAM'
                                if label == 'sports ball':
                                    coords = (xmin, ymin)
                                    loc[coords] = 'Soccer Ball'

                  ## print color next to the person
                    for key in loc.keys():
                        text_pos = str(loc[key])
                        cv2.putText(image_np, text_pos, (key[0], key[1]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 0, 0), 2) # Text in black

                    if all_xmax:
                        #print('line!')
                        xmax_max = max(all_xmax)
                        xmin_min = min(all_xmin)
                        cv2.line(image_np, (xmin_min, 0), (xmin_min, height), (255, 0, 0), 2)
                        cv2.line(image_np, (xmax_max, 0), (xmax_max, height), (0, 0, 255), 2)

                cv2.imshow('image', image_np)
                out.write(image_np)

                if cv2.waitKey(10) & 0xFF == ord('q'):
                    cv2.destroyAllWindows()
                    cap.release()
                    break
    print("--------------------------Finishing tracking video--------------------------\n")
    out.release()


if __name__ == '__main__':
    main()

