const showToast = (message, type = 'success') => {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} slide-in`;
    
    let icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    if (type === 'warning') icon = 'fa-exclamation-triangle';
    if (type === 'info') icon = 'fa-info-circle';

    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <span>${message}</span>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    const removeToast = () => {
        toast.classList.replace('slide-in', 'slide-out');
        setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast-close').onclick = removeToast;

    if (type !== 'error') {
        setTimeout(removeToast, 3000);
    }
};

// Handle Django messages on load
document.addEventListener('DOMContentLoaded', () => {
    const messages = document.querySelectorAll('.django-message');
    messages.forEach(msg => {
        showToast(msg.textContent, msg.dataset.type);
    });
});
