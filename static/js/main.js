document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const toggleButton = document.getElementById('sidebar-toggle');

    // Check if mobile (viewport width <= 768px)
    const isMobile = window.matchMedia('(max-width: 768px)').matches;

    // Load sidebar state from localStorage or default to closed on mobile
    let isSidebarClosed = localStorage.getItem('sidebarClosed') === 'true';
    if (isMobile && localStorage.getItem('sidebarClosed') === null) {
        isSidebarClosed = true; // Default to closed on mobile if no preference saved
    }

    if (isSidebarClosed) {
        sidebar.classList.add('closed');
        toggleButton.querySelector('.open-icon').style.display = 'none';
        toggleButton.querySelector('.close-icon').style.display = 'inline';
    } else {
        sidebar.classList.remove('closed');
        toggleButton.querySelector('.open-icon').style.display = 'inline';
        toggleButton.querySelector('.close-icon').style.display = 'none';
    }

    // Toggle sidebar on button click
    toggleButton.addEventListener('click', () => {
        sidebar.classList.toggle('closed');
        const isClosed = sidebar.classList.contains('closed');
        toggleButton.querySelector('.open-icon').style.display = isClosed ? 'none' : 'inline';
        toggleButton.querySelector('.close-icon').style.display = isClosed ? 'inline' : 'none';
        localStorage.setItem('sidebarClosed', isClosed);
    });

    // Update sidebar state on window resize
    window.addEventListener('resize', () => {
        const isNowMobile = window.matchMedia('(max-width: 768px)').matches;
        if (isNowMobile && localStorage.getItem('sidebarClosed') === null) {
            sidebar.classList.add('closed');
            toggleButton.querySelector('.open-icon').style.display = 'none';
            toggleButton.querySelector('.close-icon').style.display = 'inline';
            localStorage.setItem('sidebarClosed', true);
        }
    });
});