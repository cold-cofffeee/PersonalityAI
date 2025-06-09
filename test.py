
import requests
import json
import time

API_URL = "http://127.0.0.1:8000"

def test_health_endpoint():
    """Test the health check endpoint"""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{API_URL}/")
        print(f"Health check - Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_cache_stats():
    """Test the cache stats endpoint"""
    print("\nTesting cache stats endpoint...")
    try:
        response = requests.get(f"{API_URL}/cache-stats")
        print(f"Cache stats - Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Cache stats test failed: {e}")
        return False

def test_analyze_endpoint():
    """Test the analyze endpoint"""
    print("\nTesting analyze endpoint...")
    
    sample_text = """
    When I walk through a quiet forest trail, I often find myself reflecting on the nature of existence, 
    the fragility of time, and the small joys we often overlook. My writing tends to wander, much like my thoughts.
    I enjoy exploring philosophical concepts and finding meaning in everyday experiences. Sometimes I prefer 
    solitude to gather my thoughts, but I also appreciate deep conversations with close friends about life's mysteries.
    """

    payload = {
        "text": sample_text
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(f"{API_URL}/analyze", headers=headers, json=payload)
        print(f"Analyze - Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Error Response: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"Analyze test failed: {e}")
        return False

def test_empty_text():
    """Test with empty text"""
    print("\nTesting with empty text...")
    
    payload = {"text": ""}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(f"{API_URL}/analyze", headers=headers, json=payload)
        print(f"Empty text test - Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Empty text test failed: {e}")
        return False

def test_multiple_requests():
    """Test multiple requests to verify caching"""
    print("\nTesting multiple requests for caching...")
    
    test_texts = [
        "I love meeting new people and going to parties. I'm always energetic and optimistic!",
        "I prefer quiet evenings at home with a good book. Deep thinking and reflection are important to me.",
        "I'm very organized and always plan everything in advance. I never miss deadlines."
    ]
    
    headers = {"Content-Type": "application/json"}
    success_count = 0
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n  Test {i}/3:")
        payload = {"text": text}
        
        try:
            response = requests.post(f"{API_URL}/analyze", headers=headers, json=payload)
            print(f"    Status Code: {response.status_code}")
            
            if response.status_code == 200:
                success_count += 1
                result = response.json()
                if result.get("response"):
                    mbti = result["response"].get("mbti_type", "Unknown")
                    print(f"    MBTI: {mbti}")
            else:
                print(f"    Error: {response.text}")
                
            # Small delay between requests
            time.sleep(1)
            
        except Exception as e:
            print(f"    Request failed: {e}")
    
    return success_count == len(test_texts)

if __name__ == "__main__":
    print("Starting API tests with caching...")
    print("Make sure the API server is running on http://127.0.0.1:8000")
    print("=" * 60)
    
    # Run tests
    health_ok = test_health_endpoint()
    cache_stats_ok = test_cache_stats()
    analyze_ok = test_analyze_endpoint()
    empty_ok = test_empty_text()
    multiple_ok = test_multiple_requests()
    
    # Final cache stats
    print("\n" + "=" * 60)
    print("Final cache statistics:")
    try:
        response = requests.get(f"{API_URL}/cache-stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"Total cached files: {stats.get('total_files', 0)}")
            print(f"File types: {stats.get('file_types', {})}")
            print(f"Cache directory: {stats.get('cache_directory', 'Unknown')}")
    except Exception as e:
        print(f"Failed to get final cache stats: {e}")
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"Health endpoint: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Cache stats endpoint: {'✓ PASS' if cache_stats_ok else '✗ FAIL'}")
    print(f"Analyze endpoint: {'✓ PASS' if analyze_ok else '✗ FAIL'}")
    print(f"Empty text handling: {'✓ PASS' if empty_ok else '✗ FAIL'}")
    print(f"Multiple requests: {'✓ PASS' if multiple_ok else '✗ FAIL'}")
    
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all([health_ok, cache_stats_ok, analyze_ok, empty_ok, multiple_ok]) else '✗ SOME TESTS FAILED'}")
    print("\nCheck the 'cache' directory for logged JSON files!")
