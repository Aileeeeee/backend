# How Django Loads `.env` Values Into `settings`

## The Confusion Most Beginners Have

A lot of beginners wonder:

> “If my secret keys are inside a `.env` file, why am I accessing them using `settings.AT_API_KEY` instead of reading directly from `.env`?”

The answer is:

Django does **not** read `.env` files automatically.

Your `.env` values are first loaded into `settings.py`, and then Django exposes them through:

```python
from django.conf import settings
```

---

# The Full Flow

```text
.env  →  settings.py  →  django.conf.settings
```

This means:

1. Your secrets live in `.env`
2. `settings.py` loads them
3. Django stores them inside the `settings` object
4. Your app accesses them anywhere using:

```python
settings.YOUR_VARIABLE
```

---

# Step-by-Step Example

## Step 1 — Store Variables in `.env`

```env
AT_USERNAME=sandbox
AT_API_KEY=my_secret_key
```

---

## Step 2 — Load Them in `settings.py`

### Option A — Using `python-decouple`

Install:

```bash
pip install python-decouple
```

Then inside `settings.py`:

```python
from decouple import config

AT_USERNAME = config("AT_USERNAME")
AT_API_KEY = config("AT_API_KEY")
```

---

### Option B — Using `django-environ`

Install:

```bash
pip install django-environ
```

Then inside `settings.py`:

```python
import environ

env = environ.Env()
environ.Env.read_env()

AT_USERNAME = env("AT_USERNAME")
AT_API_KEY = env("AT_API_KEY")
```

---

# Step 3 — Access Them Anywhere in Django

Now anywhere in your project:

```python
from django.conf import settings
```

You can access:

```python
settings.AT_USERNAME
settings.AT_API_KEY
```

Example:

```python
import africastalking
from django.conf import settings

africastalking.initialize(
    username=settings.AT_USERNAME,
    api_key=settings.AT_API_KEY,
)
```

---

# What `settings` Actually Is

Think of `settings` as:

```python
A giant Python object containing everything from settings.py
```

So this:

```python
settings.AT_API_KEY
```

is basically Django giving you access to:

```python
AT_API_KEY = config("AT_API_KEY")
```

from inside `settings.py`.

---

# Why This Is Better Than Reading `.env` Everywhere

Instead of loading `.env` in every file:

```python
# BAD PRACTICE
from decouple import config
api_key = config("AT_API_KEY")
```

Django centralizes configuration inside `settings.py`.

Advantages:

* Cleaner architecture
* Easier maintenance
* Better security practices
* One source of truth
* Easier deployment
* Easier testing

---

# Important Security Reminder

Never hardcode secret keys directly:

```python
AT_API_KEY = "123456"
```

Use `.env` instead.

Also add `.env` to `.gitignore`:

```gitignore
.env
```

This prevents secrets from being pushed to GitHub.

---

# Quick Mental Model

Whenever you see:

```python
from django.conf import settings
```

Think:

> “Django is giving me access to variables already loaded from `settings.py`.”

And remember:

```text
.env → settings.py → settings object → entire Django app
```
