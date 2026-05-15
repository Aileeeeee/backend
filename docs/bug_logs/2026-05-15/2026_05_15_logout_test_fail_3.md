## Failure 1: `test_logout_with_valid_token_returns_200`

### The Symptom

```text
AssertionError: 400 != 200

```

Your `LogoutView` returned a `400 Bad Request`. Looking back at our architectural update, the `LogoutView` now requires the **refresh token** in the request body so it can blacklist it:

```python
refresh_token = request.data["refresh"]  # If this is missing, it raises a KeyError -> 400 Bad Request

```

### The Fix

In your test, you didn't pass the refresh token in the POST body. Update `test_logout_with_valid_token_returns_200` to include the refresh token:

```python
def test_logout_with_valid_token_returns_200(self):
    # Get both tokens from your setUp login response
    # (Assuming your setUp extracts self.refresh_token along with self.token)
    
    self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
    
    # Pass the refresh token in the body
    response = self.client.post(
        '/api/auth/logout/', 
        {'refresh': self.refresh_token}, 
        format='json'
    )
    self.assertEqual(response.status_code, status.HTTP_200_OK)

```

*(Make sure that your `LogoutTest.setUp()` method saves `self.refresh_token = response.data['tokens']['refresh']` so it's accessible here).*

---

## Failure 2: `test_token_invalid_after_logout`

### The Symptom

```text
AssertionError: 404 != 401

```

Step 5 of this test hit a wall because the endpoint `/api/auth/token/refresh/` returned a **404 Not Found**.

### The Fix

This means the routing path for your token refresh view isn't quite matching that exact string in your project's main `urls.py`.

Check your main `urls.py` file. SimpleJWT refresh endpoints are usually structured in one of two ways. Update step 5 in your test code to use whichever path matches your routing configuration:

**Option A (If nested under auth):**

```python
refresh_response = self.client.post('/api/auth/refresh/', {'refresh': refresh_token}, format='json')

```

**Option B (If sitting directly under token root):**

```python
refresh_response = self.client.post('/api/token/refresh/', {'refresh': refresh_token}, format='json')

```

### Double-check your `urls.py` config

For context, your `urls.py` setup should look something like this to match Option A:

```python
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # ... your other auth paths
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

```

---

## Bug Doc Cheat Sheet for these fixes

| Bug | Trigger | Culprit | Fix |
| --- | --- | --- | --- |
| **400 on Logout View** | Sending empty payload to `LogoutView` | View expects `{"refresh": "..."}` payload to pass to the blacklist mechanics. | Pass the refresh token inside the payload format. |
| **404 on Token Refresh** | Requesting `/api/auth/token/refresh/` | URL string mismatch with the actual endpoint route registered in Django's routing table. | Adjust the test string to target the correct path structure mapped to `TokenRefreshView`. |