from flask import Flask, render_template, request, send_from_directory, redirect
import os
import sqlite3
import uuid
from tasks import generate_images
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = "upload"
DATABASE = "jobs.db"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    return sqlite3.connect(DATABASE, timeout=30)

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        prompt1 TEXT,
        prompt2 TEXT,
        prompt3 TEXT,
        image_path TEXT,
        zip_path TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory("upload", filename)

@app.route("/zips/<filename>")
def zip_file(filename):
    return send_from_directory("zips", filename)

@app.route("/generate/<id>/<filename>")
def generate_file(id, filename):
    return send_from_directory(f"generated/{id}", filename)

@app.route("/")
def home():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs ORDER BY id")
    jobs = cursor.fetchall()

    conn.close()

    return render_template("index.html", jobs=jobs)

@app.route("/job-stats")
def job_stats():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Processing'")
    queued = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Done'")
    success = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM jobs WHERE status='Failed'")
    failed = cursor.fetchone()[0]

    return {
        "total": total,
        "queued": queued,
        "success": success,
        "failed": failed
    }

@app.route("/jobs")
def jobs():

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    rows = cursor.fetchall()

    jobs = []
    for r in rows:
        jobs.append({
            "id": r[0],
            "title": r[1],
            "reference": r[5],
            "status": r[7],
            "zip": f"{r[6]}",
            "img1": f"/generate/{r[0]}/image_{r[0]}_1.png" if os.path.exists(f"generated/{r[0]}/image_{r[0]}_1.png") else "/static/img/image.png",
            "img2": f"/generate/{r[0]}/image_{r[0]}_2.png" if os.path.exists(f"generated/{r[0]}/image_{r[0]}_2.png") else "/static/img/image.png",
            "img3": f"/generate/{r[0]}/image_{r[0]}_3.png" if os.path.exists(f"generated/{r[0]}/image_{r[0]}_3.png") else "/static/img/image.png",
        })

    conn.close()

    return {"data": jobs}


@app.route("/create-job", methods=["POST"])
def create_job():
    reference = request.files['reference']
    title = request.form['title']
    prompt1 = request.form['prompt1']
    prompt2 = request.form['prompt2']
    prompt3 = request.form['prompt3']

    ext = os.path.splitext(reference.filename)[1]
    filename = str(uuid.uuid4()) + ext

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    reference.save(filepath)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO jobs (title, prompt1, prompt2, prompt3, image_path, status) VALUES (?, ?, ?, ?, ?, ?)",
        (title, prompt1, prompt2, prompt3, filename, "queued")
    )

    job_id = cursor.lastrowid
    generate_images.delay(job_id)

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete-job/<id>")
def delete_job(id):

    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id=?", (id,))
    job = cursor.fetchone()

    if job:

        image_path = os.path.join(app.config["UPLOAD_FOLDER"], job[5])

        if os.path.exists(image_path):
            os.remove(image_path)

        if os.path.exists(f"generated/{id}"):
            shutil.rmtree(f"generated/{id}")

        zip_path = job[6]
        if zip_path:
            if os.path.exists(zip_path):
                os.remove(zip_path)

        cursor.execute(
            "DELETE FROM jobs where id=?",
            (id,)
        )

        conn.commit()
    conn.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)