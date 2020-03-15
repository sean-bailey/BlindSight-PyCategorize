# -*- coding: utf-8 -*-
import boto3
import uuid
s3 = boto3.client('s3')
rekognition=boto3.client('rekognition')
dynamodb = boto3.client('dynamodb')
dynamoDBTable="LatestAlexaTable"
from datetime import datetime


def getlabels(bucket,key):
    labelresponse = rekognition.detect_labels(
    Image={
    'S3Object':{
    'Bucket':bucket,
    'Name':key
    }
    },
    MaxLabels=3,
    MinConfidence=80.0
    )
    return labelresponse

#we gonna do some cool shit with them bounding boxes. Basically it provides
#top and left based on reference from the top and left of the scren.
#1 = all the way at the bottom, all the way to the right... meaning we can
#easily set thresholds. Let's do 25/50/75, Left, center, right, top, center,
#bottom.


def getfaces(bucket,key):
    response = rekognition.detect_faces(
    Image={
        'S3Object': {
            'Bucket':bucket,
            'Name': key,

        }
    },
    Attributes=[
        'ALL',
    ]
)
    return response


def gettext(bucket,key):
    response = rekognition.detect_text(
    Image={

        'S3Object': {
            'Bucket': bucket,
            'Name': key,

        }
    }
)
    return response

def getleftorright(leftvalue):
    if leftvalue < .15:
        return "Leftmost"
    elif leftvalue >=.15 and leftvalue< .4:
        return "Left"
    elif leftvalue >.6 and leftvalue <=.85:
        return "Right"
    elif leftvalue > .85:
        return "Rightmost"
    else:
        return "Center"


def gettoporbottom(topvalue):
    if topvalue < .15:
        return "Top"
    elif topvalue >=.15 and topvalue< .4:
        return "Upper"
    elif topvalue >.6 and topvalue <=.85:
        return "Lower"
    elif topvalue > .85:
        return "Bottom"
    else:
        return "Center"


#Now we need a function which will collate all findings and put them in the
#table on a per image basis
def addImageInfotoTable(labelresponse, textresponse, facesresponse):

    facedict={}
    labeldict={}
    textdict={}
    counter=1
    for face in facesresponse['FaceDetails']:
        if 'BoundingBox' in face.keys():
            topstring=gettoporbottom(face['BoundingBox']['Top'])
            leftstring = getleftorright(face['BoundingBox']['Left'])
            locationstring = topstring + " " + leftstring
            facedict["faces"+str(counter)]={
            "M":{

            "Location":{"S":str(locationstring)},
            "ageLow":{"N":str(face['AgeRange']['Low'])},
            "ageHigh":{"N":str(face['AgeRange']['High'])},
            "genderValue":{"S":str(face['Gender']['Value'])},
            "genderConf":{"N":str(face['Gender']['Confidence'])},
            "emotion":{"S":str(face['Emotions'][0]['Type'])},
            "emotionConf":{"N":str(face["Emotions"][0]['Confidence'])}
            }
            #"Location":locationstring,
            #"ageLow":face['AgeRange']['Low'],
            #"ageHigh":face["AgeRange"]["High"],
            #"genderValue":face["Gender"]["Value"],
            #"genderConf":face["Gender"]["Confidence"],
            #"emotionType1":face['Emotions'][0]['Type'],
            #"emotionConf1":face['Emotions'][0]['Confidence'],
            #"emotionType2":face['Emotions'][1]['Type'],
            #"emotionConf2":face['Emotions'][1]['Confidence'],
            #"faceId": str(uuid.uuid1())
            }
            counter +=1
    counter = 1
    for label in labelresponse['Labels']:
        for instance in label['Instances']:
            if 'BoundingBox' in instance.keys():
                topstring=gettoporbottom(instance['BoundingBox']["Top"])
                leftstring=getleftorright(instance['BoundingBox']["Left"])
                locationstring = topstring + " " + leftstring
                labeldict["labels"+str(counter)]={"L":[{"S":str(label['Name'])},{"S":str(locationstring)}]}
                counter +=1
    counter = 1
    for text in textresponse['TextDetections']:
        if 'Geometery' in text.keys():
            topstring=gettoporbottom(text['Geometery']['BoundingBox']['Top'])
            leftstring = getleftorright(text['Geometery']['BoundingBox']['Left'])
            locationstring = topstring + " " + leftstring
            textdict["text"+str(counter)]={"L":[{"S":str(text['DetectedText'])},{"S":str(locationstring)}]}
            counter +=1
    counter = 1

    #add to table somehow. Think of organization.
    #3 dictionaries, one is a dict of dicts, the other two are dicts of lists
    currenttime=str(datetime.now().toordinal())
    dynamodb.put_item(
    TableName=dynamoDBTable,
    Item={
    'id':{
    'N':"1"

    },
    'timestamp':{
    'N':currenttime
    },
    'FaceDict':{
    'M':facedict

    },
    'LabelDict':{
    'M':labeldict

    },
    'TextDict':{
    'M':textdict
    }
    }
    )


def handler(event, context):
    sourceBucket=event['Records'][0]['s3']['bucket']['name']
    sourceKey=event['Records'][0]['s3']['object']['key']
    imagelabels=getlabels(sourceBucket,sourceKey)
    imagefaces=getfaces(sourceBucket,sourceKey)
    imagetext=gettext(sourceBucket,sourceKey)
    addImageInfotoTable(imagelabels, imagetext, imagefaces)
    s3.delete_object(
    Bucket=sourceBucket,
    Key=sourceKey
    )
    return "Done!"
