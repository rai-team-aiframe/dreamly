/**
 * Posts related JavaScript functionality
 */

document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a single post page
    const postIdMatch = window.location.pathname.match(/\/post\/(\d+)/);
    if (postIdMatch) {
        const postId = postIdMatch[1];
        loadSinglePost(postId);
    }
    
    // Initialize any post containers
    initPostActions();
});

/**
 * Initialize post actions (like, share, etc.)
 */
function initPostActions() {
    // Like buttons
    document.querySelectorAll('.like-btn').forEach(btn => {
        if (!btn.hasAttribute('data-initialized')) {
            const postId = btn.closest('[data-post-id]').dataset.postId;
            btn.addEventListener('click', () => handleLike(postId, btn));
            btn.setAttribute('data-initialized', 'true');
        }
    });
    
    // Share buttons
    document.querySelectorAll('.share-btn').forEach(btn => {
        if (!btn.hasAttribute('data-initialized')) {
            const postId = btn.closest('[data-post-id]').dataset.postId;
            btn.addEventListener('click', () => handleShare(postId));
            btn.setAttribute('data-initialized', 'true');
        }
    });
}

/**
 * Handle like button click
 */
async function handleLike(postId, likeBtn) {
    try {
        const response = await window.app.likePost(postId, likeBtn);
        
        // Update UI
        const likeIcon = likeBtn.querySelector('i');
        const likeCount = likeBtn.querySelector('.post-action-count');
        
        if (response.action === 'liked') {
            likeBtn.classList.add('liked');
            if (likeIcon) likeIcon.classList.replace('far', 'fas');
        } else {
            likeBtn.classList.remove('liked');
            if (likeIcon) likeIcon.classList.replace('fas', 'far');
        }
        
        if (likeCount) {
            likeCount.textContent = response.like_count;
        }
    } catch (error) {
        console.error('Error liking post:', error);
        window.app.showToast('Error updating like status', 'error');
    }
}

/**
 * Handle share button click
 */
function handleShare(postId) {
    const postUrl = `${window.location.origin}/post/${postId}`;
    
    // If Web Share API is available
    if (navigator.share) {
        navigator.share({
            title: 'Check out this post on ImageShare',
            text: 'I found this amazing AI-generated image on ImageShare',
            url: postUrl
        })
        .catch(err => console.error('Error sharing:', err));
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(postUrl)
            .then(() => window.app.showToast('Link copied to clipboard', 'success'))
            .catch(err => console.error('Error copying:', err));
    }
}

/**
 * Load a single post
 */
async function loadSinglePost(postId) {
    const postContainer = document.getElementById('singlePost');
    if (!postContainer) return; // Not on single post page
    
    try {
        postContainer.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
            </div>
        `;
        
        // Fetch post data
        const post = await window.app.apiRequest(`/posts/${postId}`);
        
        // Render the post
        renderSinglePost(post, postContainer);
        
    } catch (error) {
        console.error('Error loading post:', error);
        postContainer.innerHTML = `
            <div class="alert alert-danger">
                <h3>Error Loading Post</h3>
                <p>There was an error loading this post. It may have been deleted or is unavailable.</p>
                <a href="/" class="btn btn-primary">Go to Home Page</a>
            </div>
        `;
    }
}

/**
 * Render a single post
 */
function renderSinglePost(post, container) {
    const postHtml = `
        <div class="single-post" data-post-id="${post.id}">
            <div class="single-post-header">
                <div class="post-user">
                    <a href="/profile/${post.username}">
                        <img src="/static/img/default-avatar.png" alt="${post.username}'s Avatar" class="post-user-avatar">
                        <div class="post-user-info">
                            <h3>${post.username}</h3>
                        </div>
                    </a>
                </div>
                <div class="post-time">
                    ${window.app.formatDate(post.created_at)}
                </div>
            </div>
            
            <div class="single-post-image">
                <img src="data:image/jpeg;base64,${post.image_data}" alt="Post Image">
            </div>
            
            <div class="single-post-actions">
                <button class="post-action-btn like-btn ${post.liked_by_user ? 'liked' : ''}">
                    <i class="${post.liked_by_user ? 'fas' : 'far'} fa-heart"></i>
                    <span class="post-action-count">${post.like_count}</span>
                </button>
                <button class="post-action-btn share-btn">
                    <i class="far fa-share-square"></i>
                    <span>Share</span>
                </button>
            </div>
            
            <div class="single-post-content">
                ${post.caption ? `<p class="single-post-caption">${post.caption}</p>` : ''}
                <p class="single-post-prompt"><strong>Prompt:</strong> ${post.prompt}</p>
            </div>
            
            <div class="single-post-comments">
                <h3>Comments</h3>
                <div class="comments-container">
                    <p class="text-center text-muted">Comments coming soon...</p>
                </div>
            </div>
        </div>
    `;
    
    container.innerHTML = postHtml;
    
    // Initialize post actions
    initPostActions();
}

/**
 * Create a new post
 */
async function createPost(promptText, caption = '', imageData = null) {
    try {
        const postData = {
            prompt: promptText,
            caption: caption
        };
        
        if (imageData) {
            postData.image_data = imageData;
        }
        
        const response = await window.app.apiRequest('/posts', 'POST', postData);
        return response;
    } catch (error) {
        console.error('Error creating post:', error);
        throw error;
    }
}