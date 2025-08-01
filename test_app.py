#!/usr/bin/env python3
"""
Test script for the Timelapse Generator application
"""

import requests
import time
import os
import tempfile
from PIL import Image
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_IMAGES_COUNT = 10

def create_test_images(folder_path):
    """Create test images for testing"""
    os.makedirs(folder_path, exist_ok=True)
    
    for i in range(TEST_IMAGES_COUNT):
        # Create a simple test image
        img = Image.new('RGB', (640, 480), color=(i * 25, 100, 150))
        img.save(os.path.join(folder_path, f"test_image_{i:03d}.jpg"))
    
    print(f"Created {TEST_IMAGES_COUNT} test images in {folder_path}")

def test_system_info():
    """Test system info endpoint"""
    print("Testing system info...")
    try:
        response = requests.get(f"{BASE_URL}/api/system/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ System info: CPU cores={data['cpu_count']}, Memory={data['memory_total_mb']:.1f}MB")
            return True
        else:
            print(f"✗ System info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ System info error: {e}")
        return False

def test_create_timelapse(input_folder, output_folder):
    """Test creating a timelapse"""
    print("Testing timelapse creation...")
    
    request_data = {
        "input_folder": input_folder,
        "output_folder": output_folder,
        "fps": 10,
        "resolution": "640x480",
        "output_format": "mp4",
        "compression_quality": "ultrafast",
        "cpu_limit": 50,
        "memory_limit_mb": 512
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/timelapse", json=request_data)
        if response.status_code == 200:
            job_data = response.json()
            print(f"✓ Timelapse job created: {job_data['job_id']}")
            return job_data['job_id']
        else:
            print(f"✗ Timelapse creation failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"✗ Timelapse creation error: {e}")
        return None

def test_job_status(job_id):
    """Test job status monitoring"""
    print(f"Monitoring job {job_id}...")
    
    max_wait = 60  # Maximum wait time in seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{BASE_URL}/api/job/{job_id}")
            if response.status_code == 200:
                job_data = response.json()
                print(f"  Status: {job_data['status']}, Progress: {job_data['progress']:.1f}%, Message: {job_data['message']}")
                
                if job_data['status'] == 'completed':
                    print("✓ Job completed successfully!")
                    return True
                elif job_data['status'] == 'failed':
                    print(f"✗ Job failed: {job_data['message']}")
                    return False
                
                time.sleep(2)
            else:
                print(f"✗ Job status check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Job status error: {e}")
            return False
    
    print("✗ Job monitoring timeout")
    return False

def test_download(job_id):
    """Test video download"""
    print("Testing video download...")
    try:
        response = requests.get(f"{BASE_URL}/api/download/{job_id}")
        if response.status_code == 200:
            # Save the video file
            output_file = f"test_output_{job_id[:8]}.mp4"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f"✓ Video downloaded: {output_file}")
            return True
        else:
            print(f"✗ Download failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Download error: {e}")
        return False

def test_validation():
    """Test input validation"""
    print("Testing input validation...")
    
    # Test invalid input folder
    request_data = {
        "input_folder": "/nonexistent/folder",
        "output_folder": "/tmp/test_output",
        "fps": 30
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/timelapse", json=request_data)
        if response.status_code == 400:
            print("✓ Input validation working (rejected invalid folder)")
            return True
        else:
            print(f"✗ Input validation failed: expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Validation test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🎬 Timelapse Generator Test Suite")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("✗ Server not responding")
            return
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("Make sure the application is running on http://localhost:8000")
        return
    
    print("✓ Server is running")
    
    # Create test directories
    test_input = "/tmp/test_input"
    test_output = "/tmp/test_output"
    
    # Create test images
    create_test_images(test_input)
    
    # Run tests
    tests = [
        ("System Info", test_system_info),
        ("Input Validation", test_validation),
    ]
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if not test_func():
            print(f"✗ {test_name} test failed")
            continue
    
    # Test timelapse creation
    print(f"\n--- Timelapse Creation ---")
    job_id = test_create_timelapse(test_input, test_output)
    if job_id:
        if test_job_status(job_id):
            test_download(job_id)
    
    print("\n" + "=" * 50)
    print("🎬 Test suite completed!")

if __name__ == "__main__":
    main() 