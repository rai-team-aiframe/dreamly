/**
 * ImageShare main JavaScript file
 */

// DOM elements
const logoutBtn = document.getElementById('logoutBtn');
const mobileLogoutBtn = document.getElementById('mobileLogoutBtn');
const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
const mobileMenu = document.querySelector('.mobile-menu');
const searchInput = document.getElementById('searchInput');
const toastContainer = document.getElementById('toast-container');
const modalContainer = document.getElementById('modal-container');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const modalClose = document.querySelector('.modal-close');
const modalOverlay = document.querySelector('.modal-overlay');

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initMobileMenu();
    initLogout();
    initSearch();
    initModal();
});

/**
 * Mobile menu handling
 */
function initMobileMenu() {
    if (!mobileMenuBtn) return;
    
    mobileMenuBtn.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
    });
    
    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
        if (mobileMenu.classList.contains('active') && 
            !mobileMenu.contains(e.target) && 
            !mobileMenuBtn.contains(e.target)) {
            mobileMenu.classList.remove('active');
        }
    });
}

/**
 * Logout functionality
 */
function initLogout() {
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    if (mobileLogoutBtn) {
        mobileLogoutBtn.addEventListener('click', handleLogout);
    }
}

async function handleLogout(e) {
    e.preventDefault();
    
    try {
        // Clear token cookie
        document.cookie = 'access_token=; Max-Age=0; path=/;';
        
        // Redirect to login page
        window.location.href = '/login';
    } catch (error) {
        showToast('Error logging out. Please try again.', 'error');
    }
}

/**
 * Search functionality
 */
function initSearch() {
    if (!searchInput) return;
    
    // Implement search with debounce
    let searchTimeout;
    
    searchInput.addEventListener('keyup', (e) => {
        clearTimeout(searchTimeout);
        
        if (e.key === 'Enter') {
            // Immediate search on Enter
            performSearch(searchInput.value);
        } else {
            // Debounce for other keystrokes
            searchTimeout = setTimeout(() => {
                if (searchInput.value.trim().length >= 2) {
                    performSearch(searchInput.value);
                }
            }, 500);
        }
    });
}

function performSearch(query) {
    if (query.trim().length === 0) return;
    
    // Redirect to search page with query
    window.location.href = `/search?q=${encodeURIComponent(query)}`;
}

/**
 * Modal functionality
 */
function initModal() {
    if (!modalContainer) return;
    
    // Close modal when clicking close button or overlay
    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', closeModal);
}

function openModal(title, content) {
    modalTitle.textContent = title;
    modalBody.innerHTML = content;
    modalContainer.classList.remove('modal-hidden');
    document.body.style.overflow = 'hidden'; // Prevent scrolling
}

function closeModal() {
    modalContainer.classList.add('modal-hidden');
    document.body.style.overflow = ''; // Re-enable scrolling
}

/**
 * Toast notifications
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'exclamation-circle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon} toast-icon"></i>
        <div class="toast-message">${message}</div>
        <button class="toast-close">&times;</button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Add event listener to close button
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });
    
    // Automatically remove toast after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, duration);
}

/**
 * API requests helper
 */
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        },
        credentials: 'include' // Include cookies
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Something went wrong');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

/**
 * Date formatting
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffMinutes = Math.floor(diffTime / (1000 * 60));
    const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffMinutes < 60) {
        return diffMinutes === 1 ? '1 minute ago' : `${diffMinutes} minutes ago`;
    } else if (diffHours < 24) {
        return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
    } else if (diffDays < 7) {
        return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    }
}

/**
 * Image handling
 */
function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

/**
 * Like post functionality
 */
async function likePost(postId, likeButton) {
    try {
        const response = await apiRequest(`/posts/like/${postId}`, 'POST');
        const likeCount = likeButton.querySelector('.post-action-count');
        
        if (response.action === 'liked') {
            likeButton.classList.add('liked');
            showToast('Post liked successfully', 'success');
        } else {
            likeButton.classList.remove('liked');
            showToast('Post unliked', 'info');
        }
        
        // Update like count
        if (likeCount) {
            likeCount.textContent = response.like_count;
        }
        
        return response;
    } catch (error) {
        showToast('Error updating like status', 'error');
        throw error;
    }
}

/**
 * Follow user functionality
 */
async function followUser(userId, followButton) {
    try {
        const response = await apiRequest(`/users/follow/${userId}`, 'POST');
        
        if (response.action === 'followed') {
            followButton.textContent = 'Unfollow';
            followButton.classList.remove('btn-primary');
            followButton.classList.add('btn-secondary');
            showToast('User followed successfully', 'success');
        } else {
            followButton.textContent = 'Follow';
            followButton.classList.remove('btn-secondary');
            followButton.classList.add('btn-primary');
            showToast('User unfollowed', 'info');
        }
        
        return response;
    } catch (error) {
        showToast('Error updating follow status', 'error');
        throw error;
    }
}

/**
 * Form validation helper
 */
function validateForm(form) {
    const inputs = form.querySelectorAll('input, textarea, select');
    let isValid = true;
    
    inputs.forEach(input => {
        if (input.hasAttribute('required') && !input.value.trim()) {
            markInvalid(input, 'This field is required');
            isValid = false;
        } else if (input.type === 'email' && input.value.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(input.value.trim())) {
                markInvalid(input, 'Please enter a valid email address');
                isValid = false;
            } else {
                markValid(input);
            }
        } else if (input.type === 'password' && input.dataset.minLength) {
            const minLength = parseInt(input.dataset.minLength);
            if (input.value.length < minLength) {
                markInvalid(input, `Password must be at least ${minLength} characters`);
                isValid = false;
            } else {
                markValid(input);
            }
        } else {
            markValid(input);
        }
    });
    
    return isValid;
}

function markInvalid(input, message) {
    // Add error class to input
    input.classList.add('is-invalid');
    
    // Find or create error message element
    let errorElement = input.parentElement.querySelector('.form-error');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'form-error';
        input.parentElement.appendChild(errorElement);
    }
    
    errorElement.textContent = message;
}

function markValid(input) {
    // Remove error class
    input.classList.remove('is-invalid');
    
    // Remove error message if exists
    const errorElement = input.parentElement.querySelector('.form-error');
    if (errorElement) {
        errorElement.remove();
    }
}

/**
 * Base64 image utilities
 */
function dataURItoBlob(dataURI) {
    const byteString = atob(dataURI.split(',')[1]);
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    
    return new Blob([ab], { type: mimeString });
}

/**
 * Export functions for use in other scripts
 */
window.app = {
    showToast,
    apiRequest,
    formatDate,
    openModal,
    closeModal,
    likePost,
    followUser,
    validateForm,
    loadImage,
    dataURItoBlob
};