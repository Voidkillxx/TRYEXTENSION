const audio = new Audio('warning.mp3'); // Put a 'warning.mp3' file in your folder
audio.play().then(() => {
    setTimeout(() => window.close(), 2000); // Close after playing
});