document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    const setTheme = (isDark) => {
        html.setAttribute('data-theme', isDark ? 'dark' : 'light');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        if (themeToggle) {
            themeToggle.innerHTML = isDark ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        }
    };

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = html.getAttribute('data-theme') === 'dark';
            setTheme(!isDark);
        });
    }

    // Load initial theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme === 'dark');
});
