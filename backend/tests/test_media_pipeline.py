import asyncio
import os
import time
import uuid
import httpx


async def main():
    async with httpx.AsyncClient(base_url="http://nginx") as client:
        # 1. Register test user
        suffix = uuid.uuid4().hex[:6]
        username = f"creator_{suffix}"
        password = "Password123!"
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": password,
                "channel_name": f"Channel {username}",
            },
        )
        print("Register status:", reg.status_code)
        cookies = reg.cookies

        # 2. Upload sample.mp4
        with open("/tmp/sample.mp4", "rb") as f:
            files = {"video": ("sample.mp4", f, "video/mp4")}
            data = {
                "title": "Sample Test Video",
                "description": "Testing FFmpeg pipeline",
                "visibility": "public",
            }
            up_resp = await client.post(
                "/api/v1/videos/upload",
                data=data,
                files=files,
                cookies=cookies,
            )
        print("Upload status:", up_resp.status_code)
        video_data = up_resp.json()
        video_id = video_data["id"]
        print(f"Uploaded video {video_id}, initial status: {video_data['status']}")

        # 3. Wait for Arq worker to process video to 'ready'
        ready = False
        for i in range(30):
            await asyncio.sleep(1)
            v_resp = await client.get(f"/api/v1/videos/{video_id}", cookies=cookies)
            v_info = v_resp.json()
            curr_status = v_info["status"]
            print(f"[{i+1}s] Current video status: {curr_status}")
            if curr_status == "ready":
                ready = True
                print("Video successfully processed to ready!")
                print("Duration:", v_info.get("duration_seconds"))
                print("Thumbnail object key:", v_info.get("thumbnail_object_key"))
                break
            elif curr_status == "failed":
                print("Processing failed:", v_info.get("hidden_reason") or v_info)
                break

        assert ready, "Video did not become ready"

        # 4. Request video stream with Range header: bytes=0-1024
        headers = {"Range": "bytes=0-1024"}
        stream_resp = await client.get(
            f"/api/v1/videos/{video_id}/stream", headers=headers
        )
        print("Stream HTTP status:", stream_resp.status_code)
        print("Content-Range header:", stream_resp.headers.get("content-range"))
        print("Content-Length header:", stream_resp.headers.get("content-length"))
        print("Accept-Ranges header:", stream_resp.headers.get("accept-ranges"))
        print("Bytes received:", len(stream_resp.content))
        assert stream_resp.status_code == 206
        assert len(stream_resp.content) == 1025

        # 5. Check thumbnail access
        thumb_resp = await client.get(f"/api/v1/videos/{video_id}/thumbnail")
        print("Thumbnail HTTP status:", thumb_resp.status_code)
        print("Thumbnail content-type:", thumb_resp.headers.get("content-type"))
        assert thumb_resp.status_code == 200
        assert len(thumb_resp.content) > 0

        print("=== ALL STAGE 4 MEDIA PIPELINE CHECKS PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
