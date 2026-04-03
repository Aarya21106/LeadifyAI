import json
import urllib.request
from urllib.parse import urlparse, parse_qs
import sys

def test_oauth_flow():
    base_url = "http://localhost:8000/api/auth/gmail"
    callback_url_base = "http://localhost:8000/api/auth/gmail/callback"
    
    print("====================================")
    print(" Gmail OAuth Backend Tester Script")
    print("====================================")
    
    print("\n1. Fetching authorization URL from backend...")
    req = urllib.request.Request(base_url)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            auth_url = data.get("auth_url")
            
            # Capture the cookie returned by the server (this is our CSRF 'state')
            cookies = response.getheader('Set-Cookie')
            
            if not auth_url:
                print("Error: auth_url not found in response.")
                sys.exit(1)
                
            print("\nSuccessfully obtained Auth URL!")
    except Exception as e:
        print(f"\nFailed to fetch auth URL: {e}")
        print("Make sure your FastAPI server is running on localhost:8000")
        sys.exit(1)

    print("\n2. OPEN THIS URL IN YOUR BROWSER:")
    print(f"\n{auth_url}\n")
    print("3. Log in to Google and authorize the application.")
    print("4. Google will redirect you to the callback URL.")
    print("\nNOTE: Because you opened this in your browser manually, the browser lacks'")
    print("the CSRF cookie given to this script. The browser will encounter a '400 Bad Request'")
    print("CSRF error when it redirects back to the backend. THIS IS EXPECTED during this test!")
    
    print("\n5. Copy the FULL URL from your browser's address bar (even if it says Bad Request)")
    print("   and paste it below:")
    
    redirected_url = input("\nPaste redirected URL here: ").strip()
    
    if not redirected_url:
        print("No URL provided. Exiting.")
        sys.exit(1)
        
    try:
        parsed_url = urlparse(redirected_url)
        query_params = parse_qs(parsed_url.query)
        
        code = query_params.get("code", [""])[0]
        state = query_params.get("state", [""])[0]
        
        if not code or not state:
            print("Error: Missing 'code' or 'state' in provided URL.")
            sys.exit(1)
    except Exception as e:
        print(f"Failed to parse URL: {e}")
        sys.exit(1)
        
    print("\n6. Calling the callback endpoint via script using captured cookie & parameters...")
    
    final_callback_url = f"{callback_url_base}?code={code}&state={state}"
    
    callback_req = urllib.request.Request(final_callback_url)
    if cookies:
        # Pass the CSRF cookie back so validation succeeds
        callback_req.add_header('Cookie', cookies.split(';')[0])
        
    try:
        # We don't auto-redirect because we want to see the 302 Redirect response
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                return urllib.response.addinfourl(fp, headers, req.get_full_url(), code)

        opener = urllib.request.build_opener(NoRedirectHandler)
        response = opener.open(callback_req)
        
        print("\n====================================")
        print(f"Status Code: {response.code}") # Expected: 302
        print(f"Headers: {response.headers}")
        print("Success! If the status code above is 302, the OAuth flow completed successfully and tokens are saved in the DB.")
        print("====================================")
    except Exception as e:
        print(f"\nCallback failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_oauth_flow()
