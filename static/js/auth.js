/**
 * Authentication-related JavaScript
 */
document.addEventListener('DOMContentLoaded', () => {
    // Check which form exists on the current page
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        initLoginForm(loginForm);
    }
    
    if (registerForm) {
        initRegisterForm(registerForm);
    }
});

/**
 * Initialize login form
 */
function initLoginForm(form) {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Basic validation
        if (!window.app.validateForm(form)) {
            return;
        }
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            // Create FormData for OAuth2 password flow
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);
            
            const response = await fetch('/users/token', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed. Please check your credentials.');
            }
            
            const data = await response.json();
            
            // Store token in cookie
            document.cookie = `access_token=${data.access_token}; path=/; max-age=${7 * 24 * 60 * 60}`; // 7 days
            
            window.app.showToast('Login successful', 'success');
            
            // Redirect to home page
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            window.app.showToast(error.message || 'Login failed', 'error');
        }
    });
}

/**
 * Initialize register form
 */
function initRegisterForm(form) {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Basic validation
        if (!window.app.validateForm(form)) {
            return;
        }
        
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Check if passwords match
        if (password !== confirmPassword) {
            window.app.showToast('Passwords do not match', 'error');
            return;
        }
        
        try {
            const response = await fetch('/users/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username,
                    email,
                    password
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed');
            }
            
            window.app.showToast('Registration successful! Please login.', 'success');
            
            // Redirect to login page
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
            
        } catch (error) {
            window.app.showToast(error.message || 'Registration failed', 'error');
        }
    });
}