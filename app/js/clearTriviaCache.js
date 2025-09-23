// Function to clear cached trivia from localStorage
function clearTriviaCache() {
    localStorage.removeItem('dailyTrivia');
    localStorage.removeItem('triviaDate');
    console.log('Trivia cache cleared.');
}

// Optional: expose the function for testing via the console
window.clearTriviaCache = clearTriviaCache;
