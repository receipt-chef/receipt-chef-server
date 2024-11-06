from flask import Blueprint, render_template

video_bp = Blueprint('video', __name__)

@video_bp.route('/')
def video():
    return render_template('video.html')
