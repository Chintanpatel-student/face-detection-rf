import logging
import os

from flask import Flask, redirect, render_template, request

from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision


imag_store = os.environ.get('imag_store')

app = Flask(__name__)

@app.route('/')
def homepage():
    datastore_client = datastore.Client()

    query = datastore_client.query(kind='Faces')
    image_entities = list(query.fetch())

    return render_template('homepage.html', image_entities=image_entities)


@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    photo = request.files['file']
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(imag_store)
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)
    blob.make_public()
    vision_client = vision.ImageAnnotatorClient()
    source_uri = 'gs://{}/{}'.format(imag_store, blob.name)
    image = vision.types.Image(
        source=vision.types.ImageSource(gcs_image_uri=source_uri))
    faces = vision_client.face_detection(image).face_annotations

    if len(faces) > 0:
        face = faces[0]
        likelihoods = [
            'Unknown', 'Very sad', 'sad', 'Possible happy', 'Likely happy',
            'Very Likely happy']
        face_joy = likelihoods[face.joy_likelihood]
    else:
        face_joy = 'Unknown'

    datastore_client = datastore.Client()
    current_datetime = datetime.now()

    kind = 'Faces'
    name = blob.name

    key = datastore_client.key(kind, name)

    entity = datastore.Entity(key)
    entity['blob_name'] = blob.name
    entity['image_public_url'] = blob.public_url
    entity['timestamp'] = current_datetime
    entity['joy'] = face_joy

    datastore_client.put(entity)

    return redirect('/')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)