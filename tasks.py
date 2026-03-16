from celery_worker import celery
import os
import zipfile
import sqlite3
from gemini_image import generate_image
from dotenv import load_dotenv

load_dotenv() 

DATABASE = "data/jobs.db"

@celery.task
def generate_images(job_id):

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    try:

        cursor.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        job = cursor.fetchone()

        reference_path = f"upload/{job[5]}"

        cursor.execute("UPDATE jobs SET status='Processing' WHERE id=?", (job_id,))
        conn.commit()

        os.makedirs(f"generated/{job_id}", exist_ok=True)

        images = []

        for i in range(3):

            if job[2+i] != "":

                output_path = f"generated/{job_id}/image_{job_id}_{i+1}.png"

                generate_image(job[i+2], reference_path, output_path)

                images.append(output_path)

        zip_path = f"zips/{job[1]}_{job[0]}.zip"

        with zipfile.ZipFile(zip_path, "w") as zipf:
            for img in images:
                zipf.write(img, os.path.basename(img))

        cursor.execute(
            "UPDATE jobs SET status='Done', zip_path=? WHERE id=?",
            (zip_path, job_id)
        )

        conn.commit()

    except Exception as e:

        print("Error generating images:", e)

        cursor.execute(
            "UPDATE jobs SET status='Failed' WHERE id=?",
            (job_id,)
        )

        conn.commit()

    finally:

        conn.close()