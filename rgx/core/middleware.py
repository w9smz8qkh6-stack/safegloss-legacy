from django.shortcuts import redirect
from django.urls import reverse


class ProfileCompletionMiddleware:
    """
    Middleware to redirect authenticated users with incomplete profiles
    to the profile completion page.
    """

    # URLs that should be accessible even with incomplete profile
    EXEMPT_URLS = [
        "/complete-profile/",
        "/accounts/logout/",
        "/accounts/login/",
        "/accounts/signup/",
        "/accounts/google/",
        "/accounts/social/",
        "/offline/",
        "/sw.js",
        "/static/",
        "/admin/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is authenticated and profile is incomplete
        if request.user.is_authenticated:
            # Skip check for exempt URLs
            path = request.path
            if not any(path.startswith(url) for url in self.EXEMPT_URLS):
                # Check if profile is incomplete
                if not getattr(request.user, 'profile_completed', True):
                    return redirect('core:complete_profile')

        response = self.get_response(request)
        return response
