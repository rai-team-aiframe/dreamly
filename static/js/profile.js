/**
 * Profile page JavaScript
 */
document.addEventListener('DOMContentLoaded', () => {
    // Get profile username from URL or page data
    const profileUsername = document.querySelector('.profile-username').textContent;
    const currentPath = window.location.pathname;
    
    // Initialize profile
    initProfile(profileUsername);
    
    // Setup tabs
    setupTabs();
});

let isCurrentUserProfile = false;
let profileUser = null;

/**
 * Initialize profile page
 */
async function initProfile(username) {
    try {
        // Load profile data
        await loadProfileData(username);
        
        // Load user posts
        loadUserPosts(profileUser.id);
        
        // If on the "liked" tab, load liked posts
        if (document.querySelector('.profile-tab[data-tab="liked"]').classList.contains('active')) {
            loadLikedPosts(profileUser.id);
        }
    } catch (error) {
        console.error('Error initializing profile:', error);
        window.app.showToast('Error loading profile', 'error');
    }
}

/**
 * Load profile data from API
 */
async function loadProfileData(username) {
    try {
        // Show loading spinner
        document.getElementById('profileLoading').style.display = 'flex';
        document.getElementById('profileContent').style.display = 'none';
        
        // Fetch profile data
        profileUser = await window.app.apiRequest(`/users/profile/${username}`);
        
        // Check if this is the current user's profile
        const currentUser = await window.app.apiRequest('/users/me');
        isCurrentUserProfile = currentUser.id === profileUser.id;
        
        // Update profile UI
        updateProfileUI(profileUser);
        
        // Hide loading spinner
        document.getElementById('profileLoading').style.display = 'none';
        document.getElementById('profileContent').style.display = 'flex';
    } catch (error) {
        console.error('Error loading profile data:', error);
        window.app.showToast('Error loading profile data', 'error');
        throw error;
    }
}

/**
 * Update profile UI with user data
 */
function updateProfileUI(userData) {
    // Update profile info
    document.getElementById('profileEmail').textContent = userData.email;
    document.getElementById('profileBio').textContent = userData.bio || 'No bio yet';
    
    // Update stats
    document.getElementById('postCount').textContent = userData.post_count;
    document.getElementById('followerCount').textContent = userData.follower_count;
    document.getElementById('followingCount').textContent = userData.following_count;
    
    // Update profile actions
    const actionsContainer = document.getElementById('profileActions');
    actionsContainer.innerHTML = '';
    
    if (isCurrentUserProfile) {
        // Current user's profile - show edit button
        const editButton = document.createElement('button');
        editButton.className = 'btn btn-secondary';
        editButton.innerHTML = '<i class="fas fa-edit"></i> Edit Profile';
        editButton.addEventListener('click', openEditProfileModal);
        actionsContainer.appendChild(editButton);
    } else {
        // Another user's profile - show follow button
        const followButton = document.createElement('button');
        followButton.className = `btn ${userData.is_following ? 'btn-secondary' : 'btn-primary'}`;
        followButton.id = 'followBtn';
        followButton.textContent = userData.is_following ? 'Unfollow' : 'Follow';
        followButton.addEventListener('click', () => handleFollow(userData.id, followButton));
        actionsContainer.appendChild(followButton);
        
        // Add message button
        const messageButton = document.createElement('button');
        messageButton.className = 'btn btn-outline-primary ml-2';
        messageButton.innerHTML = '<i class="fas fa-comment"></i> Message';
        messageButton.addEventListener('click', () => {
            window.app.showToast('Messaging feature coming soon', 'info');
        });
        actionsContainer.appendChild(messageButton);
    }
    
    // Update no posts message
    const noPostsText = document.getElementById('noPostsText');
    const createPostBtn = document.getElementById('createPostBtn');
    
    if (isCurrentUserProfile) {
        noPostsText.textContent = "You haven't created any posts yet.";
        createPostBtn.style.display = 'inline-block';
    } else {
        noPostsText.textContent = `${userData.username} hasn't created any posts yet.`;
        createPostBtn.style.display = 'none';
    }
    
    // Update no likes message
    const noLikesText = document.getElementById('noLikesText');
    
    if (isCurrentUserProfile) {
        noLikesText.textContent = "You haven't liked any posts yet.";
    } else {
        noLikesText.textContent = `${userData.username} hasn't liked any posts yet.`;
    }
}

/**
 * Handle following/unfollowing a user
 */
async function handleFollow(userId, followButton) {
    try {
        const response = await window.app.followUser(userId, followButton);
        
        // Update follower count
        const followerCount = document.getElementById('followerCount');
        const currentCount = parseInt(followerCount.textContent);
        
        if (response.action === 'followed') {
            followerCount.textContent = currentCount + 1;
        } else {
            followerCount.textContent = currentCount - 1;
        }
    } catch (error) {
        console.error('Error following/unfollowing user:', error);
    }
}

/**
 * Open edit profile modal
 */
function openEditProfileModal() {
    const template = document.getElementById('editProfileTemplate');
    const modalContent = document.importNode(template.content, true);
    
    // Prefill form with current data
    modalContent.querySelector('#editEmail').value = profileUser.email;
    modalContent.querySelector('#editBio').value = profileUser.bio || '';
    
    // Handle form submission
    const form = modalContent.querySelector('#editProfileForm');
    form.addEventListener('submit', handleEditProfile);
    
    // Handle cancel button
    modalContent.querySelector('#cancelEditBtn').addEventListener('click', window.app.closeModal);
    
    // Open modal
    window.app.openModal('Edit Profile', modalContent);
}

/**
 * Handle edit profile form submission
 */
async function handleEditProfile(e) {
    e.preventDefault();
    
    const form = e.target;
    
    // Basic validation
    if (!window.app.validateForm(form)) {
        return;
    }
    
    const formData = {
        email: form.querySelector('#editEmail').value,
        bio: form.querySelector('#editBio').value
    };
    
    // Only include password if it was provided
    const password = form.querySelector('#editPassword').value;
    if (password) {
        formData.password = password;
    }
    
    try {
        // Update profile
        const updatedUser = await window.app.apiRequest('/users/me', 'PUT', formData);
        
        // Update UI
        profileUser = { ...profileUser, ...updatedUser };
        updateProfileUI(profileUser);
        
        // Close modal
        window.app.closeModal();
        
        // Show success message
        window.app.showToast('Profile updated successfully', 'success');
    } catch (error) {
        console.error('Error updating profile:', error);
        window.app.showToast('Error updating profile', 'error');
    }
}

/**
 * Setup profile tabs
 */
function setupTabs() {
    const tabs = document.querySelectorAll('.profile-tab');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab
            tab.classList.add('active');
            
            // Show corresponding content
            const tabName = tab.dataset.tab;
            document.getElementById(`${tabName}Tab`).classList.add('active');
            
            // Load content if needed
            if (tabName === 'liked' && !document.getElementById('likedPosts').hasChildNodes()) {
                loadLikedPosts(profileUser.id);
            }
        });
    });
}

/**
 * Load user posts
 */
async function loadUserPosts(userId) {
    const postsContainer = document.getElementById('userPosts');
    const loadingElement = document.getElementById('postsLoading');
    const noPostsMessage = document.getElementById('noPostsMessage');
    
    try {
        loadingElement.style.display = 'flex';
        postsContainer.innerHTML = '';
        noPostsMessage.style.display = 'none';
        
        // Fetch user posts
        const posts = await window.app.apiRequest(`/posts/user/${userId}`);
        
        loadingElement.style.display = 'none';
        
        if (posts.length === 0) {
            noPostsMessage.style.display = 'block';
            return;
        }
        
        // Render posts
        renderProfilePosts(posts, postsContainer);
    } catch (error) {
        console.error('Error loading user posts:', error);
        loadingElement.style.display = 'none';
        window.app.showToast('Error loading posts', 'error');
    }
}

/**
 * Load posts liked by the user
 */
async function loadLikedPosts(userId) {
    const postsContainer = document.getElementById('likedPosts');
    const loadingElement = document.getElementById('likedLoading');
    const noLikesMessage = document.getElementById('noLikesMessage');
    
    try {
        loadingElement.style.display = 'flex';
        postsContainer.innerHTML = '';
        noLikesMessage.style.display = 'none';
        
        // Fetch liked posts (endpoint would need to be created)
        // For now, let's simulate empty results
        const posts = []; // await window.app.apiRequest(`/users/liked/${userId}`);
        
        loadingElement.style.display = 'none';
        
        if (posts.length === 0) {
            noLikesMessage.style.display = 'block';
            return;
        }
        
        // Render posts
        renderProfilePosts(posts, postsContainer);
    } catch (error) {
        console.error('Error loading liked posts:', error);
        loadingElement.style.display = 'none';
        window.app.showToast('Error loading liked posts', 'error');
    }
}

/**
 * Render posts in the profile grid
 */
function renderProfilePosts(posts, container) {
    const template = document.getElementById('profilePostTemplate');
    
    posts.forEach(post => {
        const postEl = document.importNode(template.content, true).firstElementChild;
        
        // Set post ID
        postEl.dataset.postId = post.id;
        
        // Set post image
        const imgEl = postEl.querySelector('.profile-post-image img');
        imgEl.src = `data:image/jpeg;base64,${post.image_data}`;
        
        // Set like count
        postEl.querySelector('.profile-post-likes span').textContent = post.like_count;
        
        // Add event listener to open modal on click
        postEl.addEventListener('click', () => showPostModal(post));
        
        container.appendChild(postEl);
    });
}

/**
 * Show post modal
 */
function showPostModal(post) {
    const template = document.getElementById('postModalTemplate');
    const modalContent = document.importNode(template.content, true).firstElementChild;
    
    // Set post image
    modalContent.querySelector('.modal-post-image img').src = `data:image/jpeg;base64,${post.image_data}`;
    
    // Set username
    modalContent.querySelector('.modal-post-user-info h3').textContent = post.username;
    
    // Set user profile link
    modalContent.querySelector('.modal-post-user').href = `/profile/${post.username}`;
    
    // Set caption and prompt
    modalContent.querySelector('.modal-post-caption').textContent = post.caption || '';
    modalContent.querySelector('.modal-post-prompt span').textContent = post.prompt;
    
    // Set time
    modalContent.querySelector('.modal-post-time').textContent = window.app.formatDate(post.created_at);
    
    // Set post link
    modalContent.querySelector('.modal-post-actions a').href = `/post/${post.id}`;
    
    // Handle post options dropdown
    const optionsDropdown = modalContent.querySelector('#postOptionsDropdown');
    if (isCurrentUserProfile) {
        // Show options for current user's posts
        // Edit post
        const editBtn = optionsDropdown.querySelector('.edit-post-btn');
        editBtn.addEventListener('click', (e) => {
            e.preventDefault();
            window.app.showToast('Edit feature coming soon', 'info');
        });
        
        // Delete post
        const deleteBtn = optionsDropdown.querySelector('.delete-post-btn');
        deleteBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            
            if (confirm('Are you sure you want to delete this post? This action cannot be undone.')) {
                try {
                    await window.app.apiRequest(`/posts/${post.id}`, 'DELETE');
                    
                    // Remove post from DOM
                    const postEl = document.querySelector(`.grid-item[data-post-id="${post.id}"]`);
                    if (postEl) {
                        postEl.remove();
                    }
                    
                    // Close modal
                    window.app.closeModal();
                    
                    // Show success message
                    window.app.showToast('Post deleted successfully', 'success');
                    
                    // Decrement post count
                    const postCount = document.getElementById('postCount');
                    postCount.textContent = parseInt(postCount.textContent) - 1;
                    
                    // Show no posts message if no posts left
                    if (parseInt(postCount.textContent) === 0) {
                        document.getElementById('noPostsMessage').style.display = 'block';
                    }
                } catch (error) {
                    console.error('Error deleting post:', error);
                    window.app.showToast('Error deleting post', 'error');
                }
            }
        });
    } else {
        // Hide options for other users' posts
        optionsDropdown.style.display = 'none';
    }
    
    // Update like count
    const likeCount = modalContent.querySelector('.post-action-count');
    likeCount.textContent = post.like_count;
    
    // Set liked state
    const likeBtn = modalContent.querySelector('.modal-like-btn');
    const likeIcon = likeBtn.querySelector('i');
    
    if (post.liked_by_user) {
        likeBtn.classList.add('liked');
        likeIcon.classList.replace('far', 'fas');
    }
    
    // Add event listener for like button
    likeBtn.addEventListener('click', async () => {
        try {
            const response = await window.app.likePost(post.id, likeBtn);
            
            // Update the icon
            if (response.action === 'liked') {
                likeIcon.classList.replace('far', 'fas');
            } else {
                likeIcon.classList.replace('fas', 'far');
            }
            
            // Update the count
            likeCount.textContent = response.like_count;
            
            // Update the grid item
            const gridItem = document.querySelector(`.grid-item[data-post-id="${post.id}"]`);
            if (gridItem) {
                gridItem.querySelector('.profile-post-likes span').textContent = response.like_count;
            }
            
        } catch (error) {
            console.error('Error handling like:', error);
        }
    });
    
    // Add event listener for share button
    const shareBtn = modalContent.querySelector('.modal-share-btn');
    shareBtn.addEventListener('click', () => {
        const postUrl = `${window.location.origin}/post/${post.id}`;
        
        // If Web Share API is available
        if (navigator.share) {
            navigator.share({
                title: `Post by ${post.username}`,
                text: post.caption || 'Check out this image on ImageShare',
                url: postUrl
            })
            .catch(err => console.error('Error sharing:', err));
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(postUrl)
                .then(() => window.app.showToast('Link copied to clipboard', 'success'))
                .catch(err => console.error('Error copying:', err));
        }
    });
    
    // Open modal
    window.app.openModal(`Post by ${post.username}`, modalContent.outerHTML);
}