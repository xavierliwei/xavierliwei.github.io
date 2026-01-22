// Proactive AI Chat Application

const API_BASE_URL = 'http://localhost:8000';

// State
let state = {
    suggestions: [],
    messages: [],
    settings: {
        frequency: 'sometimes',
        topics: ['learning', 'work'],
        pauseMeetings: true,
        detectDeepWork: true,
        queueOnly: false
    },
    currentSuggestion: null,
    onboardingComplete: false,
    selectedInterests: []
};

// Storage keys
const STORAGE_KEYS = {
    MESSAGES: 'proactive_ai_messages',
    ONBOARDING: 'proactive_ai_onboarding_complete',
    SETTINGS: 'proactive_ai_settings',
    SNOOZED: 'proactive_ai_snoozed_until',
    THEME: 'proactive_ai_theme'
};

// Validation constants
const VALIDATION = {
    MAX_MESSAGE_LENGTH: 4000,
    MAX_SEARCH_LENGTH: 200,
    MIN_MESSAGE_LENGTH: 1
};

// Input validation and sanitization utilities
function sanitizeInput(input) {
    if (typeof input !== 'string') return '';
    // Remove null bytes and control characters (except newlines and tabs)
    return input.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '').trim();
}

function validateMessageLength(message) {
    if (!message || message.length < VALIDATION.MIN_MESSAGE_LENGTH) {
        return { valid: false, error: 'Message cannot be empty' };
    }
    if (message.length > VALIDATION.MAX_MESSAGE_LENGTH) {
        return { valid: false, error: `Message too long (max ${VALIDATION.MAX_MESSAGE_LENGTH} characters)` };
    }
    return { valid: true };
}

function validateSearchQuery(query) {
    if (!query || query.trim().length === 0) {
        return { valid: false, error: 'Search query cannot be empty' };
    }
    if (query.length > VALIDATION.MAX_SEARCH_LENGTH) {
        return { valid: false, error: `Search query too long (max ${VALIDATION.MAX_SEARCH_LENGTH} characters)` };
    }
    return { valid: true };
}

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const suggestionCards = document.getElementById('suggestion-cards');
const notificationBadge = document.getElementById('notification-badge');
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggle-sidebar');
const settingsBtn = document.getElementById('settings-btn');
const settingsModal = document.getElementById('settings-modal');
const transparencyModal = document.getElementById('transparency-modal');
const quickActions = document.getElementById('quick-actions');
const onboardingModal = document.getElementById('onboarding-modal');
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeApp();
    setupEventListeners();
});

// Theme management
function initializeTheme() {
    const savedTheme = localStorage.getItem(STORAGE_KEYS.THEME) || 'system';
    applyTheme(savedTheme);
    updateThemeButtons(savedTheme);
}

function applyTheme(theme) {
    const root = document.documentElement;

    if (theme === 'system') {
        // Remove explicit theme to let CSS media query handle it
        root.removeAttribute('data-theme');
    } else {
        root.setAttribute('data-theme', theme);
    }
}

function updateThemeButtons(activeTheme) {
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.theme === activeTheme);
    });
}

function setTheme(theme) {
    localStorage.setItem(STORAGE_KEYS.THEME, theme);
    applyTheme(theme);
    updateThemeButtons(theme);
}

async function initializeApp() {
    // Check if user has completed onboarding
    const onboardingComplete = localStorage.getItem(STORAGE_KEYS.ONBOARDING);
    state.onboardingComplete = onboardingComplete === 'true';

    if (!state.onboardingComplete) {
        showOnboarding();
        return;
    }

    // Load saved settings
    loadSavedSettings();

    // Load saved messages
    loadSavedMessages();

    // Show skeleton loading while fetching
    showSuggestionSkeletons();

    try {
        await fetchSuggestions();
        updateNotificationBadge();
        renderSuggestionCards();
        renderQuickActions();
    } catch (error) {
        console.error('Failed to initialize app:', error);
        // Use mock data if API is not available
        useMockData();
    }
}

function loadSavedSettings() {
    const savedSettings = localStorage.getItem(STORAGE_KEYS.SETTINGS);
    if (savedSettings) {
        try {
            const parsed = JSON.parse(savedSettings);
            state.settings = { ...state.settings, ...parsed };
        } catch (e) {
            console.error('Failed to parse saved settings:', e);
        }
    }
}

function loadSavedMessages() {
    const savedMessages = localStorage.getItem(STORAGE_KEYS.MESSAGES);
    if (savedMessages) {
        try {
            const parsed = JSON.parse(savedMessages);
            if (Array.isArray(parsed) && parsed.length > 0) {
                state.messages = parsed;
                // Render saved messages (skip the welcome message which is in HTML)
                state.messages.forEach(msg => {
                    renderSavedMessage(msg.role, msg.content, msg.metadata);
                });
            }
        } catch (e) {
            console.error('Failed to parse saved messages:', e);
        }
    }
}

function saveMessages() {
    try {
        // Save only the last 50 messages to avoid localStorage limits
        const messagesToSave = state.messages.slice(-50);
        localStorage.setItem(STORAGE_KEYS.MESSAGES, JSON.stringify(messagesToSave));
    } catch (e) {
        console.error('Failed to save messages:', e);
    }
}

function renderSavedMessage(role, content, metadata = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = role === 'assistant' ? 'AI' : 'You';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Render markdown for assistant messages, plain text for user
    if (role === 'assistant') {
        const markdownDiv = document.createElement('div');
        markdownDiv.className = 'markdown-content';
        markdownDiv.innerHTML = renderMarkdown(content);
        contentDiv.appendChild(markdownDiv);
    } else {
        const textP = document.createElement('p');
        textP.textContent = content;
        contentDiv.appendChild(textP);
    }

    if (metadata && metadata.basedOn) {
        const basedOnDiv = document.createElement('div');
        basedOnDiv.className = 'based-on';
        basedOnDiv.innerHTML = `Based on: ${metadata.basedOn}`;
        contentDiv.appendChild(basedOnDiv);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
}

function clearChatHistory() {
    state.messages = [];
    localStorage.removeItem(STORAGE_KEYS.MESSAGES);
    // Clear all messages except the welcome message
    const messages = chatMessages.querySelectorAll('.message');
    messages.forEach((msg, index) => {
        if (index > 0) { // Keep first (welcome) message
            msg.remove();
        }
    });
}

function showOnboarding() {
    openModal(onboardingModal);
    setupOnboardingListeners();
}

function setupOnboardingListeners() {
    // Step 1: Get Started
    document.getElementById('onboarding-next-1').addEventListener('click', () => {
        document.getElementById('onboarding-step-1').classList.add('hidden');
        document.getElementById('onboarding-step-2').classList.remove('hidden');
    });

    // Step 2: Interests
    const interestTags = document.querySelectorAll('.interest-tag');
    const nextBtn2 = document.getElementById('onboarding-next-2');
    const interestHint = document.getElementById('interest-hint');

    interestTags.forEach(tag => {
        tag.addEventListener('click', () => {
            tag.classList.toggle('selected');
            const selected = document.querySelectorAll('.interest-tag.selected');
            state.selectedInterests = Array.from(selected).map(t => t.dataset.interest);

            // Update button state
            if (state.selectedInterests.length >= 2) {
                nextBtn2.disabled = false;
                interestHint.textContent = `${state.selectedInterests.length} topics selected`;
            } else {
                nextBtn2.disabled = true;
                interestHint.textContent = `Select at least 2 topics (${state.selectedInterests.length}/2)`;
            }
        });
    });

    document.getElementById('onboarding-back-2').addEventListener('click', () => {
        document.getElementById('onboarding-step-2').classList.add('hidden');
        document.getElementById('onboarding-step-1').classList.remove('hidden');
    });

    document.getElementById('onboarding-next-2').addEventListener('click', () => {
        document.getElementById('onboarding-step-2').classList.add('hidden');
        document.getElementById('onboarding-step-3').classList.remove('hidden');
    });

    // Step 3: Frequency
    const frequencyInputs = document.querySelectorAll('input[name="onboarding-frequency"]');
    frequencyInputs.forEach(input => {
        input.addEventListener('change', () => {
            document.querySelectorAll('.frequency-card').forEach(card => {
                card.classList.remove('selected');
            });
            input.nextElementSibling.classList.add('selected');
        });
    });

    document.getElementById('onboarding-back-3').addEventListener('click', () => {
        document.getElementById('onboarding-step-3').classList.add('hidden');
        document.getElementById('onboarding-step-2').classList.remove('hidden');
    });

    document.getElementById('onboarding-finish').addEventListener('click', completeOnboarding);
}

async function completeOnboarding() {
    // Get selected frequency
    const frequency = document.querySelector('input[name="onboarding-frequency"]:checked').value;

    // Save settings
    state.settings.frequency = frequency;
    state.settings.topics = state.selectedInterests;
    state.onboardingComplete = true;

    // Persist to localStorage
    localStorage.setItem('proactive_ai_onboarding_complete', 'true');
    localStorage.setItem('proactive_ai_settings', JSON.stringify(state.settings));

    // Try to save to backend
    try {
        await fetch(`${API_BASE_URL}/api/preferences`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'demo_user',
                topics_of_interest: state.selectedInterests,
                frequency: frequency
            })
        });
    } catch (error) {
        console.error('Failed to save preferences to backend:', error);
    }

    // Close onboarding and initialize app
    closeModal(onboardingModal);

    // Show personalized welcome message
    addMessage('assistant', `Welcome! I've noted your interests in ${state.selectedInterests.slice(0, 3).join(', ')}${state.selectedInterests.length > 3 ? ' and more' : ''}. I'll reach out ${frequency === 'rarely' ? 'occasionally' : frequency === 'often' ? 'regularly' : 'from time to time'} with relevant suggestions. Check the sidebar for recommendations!`);

    // Load suggestions
    try {
        await fetchSuggestions();
        updateNotificationBadge();
        renderSuggestionCards();
        renderQuickActions();
    } catch (error) {
        useMockData();
    }
}

function useMockData() {
    state.suggestions = [
        {
            id: '1',
            category: 'Learning',
            title: 'Deep dive into Kafka exactly-once semantics?',
            preview: 'Based on your recent study of event sourcing, this builds naturally on what you\'ve learned.',
            relevance: 0.85,
            icon: '📚',
            signals: [
                { icon: '📖', text: 'Read 12 Kafka articles this month' },
                { icon: '🔍', text: 'Searched "consumer groups" 3 times' },
                { icon: '⏰', text: 'Optimal learning time based on your patterns' },
                { icon: '📈', text: 'Topic trending in distributed systems' }
            ],
            content: {
                title: 'Kafka Exactly-Once Semantics',
                summary: 'Understanding exactly-once delivery guarantees in Apache Kafka'
            }
        },
        {
            id: '2',
            category: 'Work Update',
            title: 'Your PR has new comments',
            preview: 'PR #234 has 3 new comments, including one blocking concern about error handling.',
            relevance: 0.92,
            icon: '💼',
            signals: [
                { icon: '🔔', text: 'PR has been open for 2 days' },
                { icon: '⚠️', text: 'Blocking comment detected' },
                { icon: '👥', text: 'Requested reviewer is available' }
            ],
            content: {
                title: 'PR Review Comments',
                summary: 'New feedback on your pull request needs attention'
            }
        },
        {
            id: '3',
            category: 'Industry News',
            title: 'EU AI Regulation Updates',
            preview: 'New requirements for recommendation systems that could affect your ML infrastructure work.',
            relevance: 0.72,
            icon: '📰',
            signals: [
                { icon: '📊', text: 'Matches your interests in ML systems' },
                { icon: '🌍', text: 'Major regulatory development' },
                { icon: '🏢', text: 'May impact your current project' }
            ],
            content: {
                title: 'EU AI Act Update',
                summary: 'New transparency requirements for AI recommendation systems'
            }
        }
    ];
    renderSuggestionCards();
    updateNotificationBadge();
    renderQuickActions();
}

async function fetchSuggestions() {
    const response = await fetch(`${API_BASE_URL}/api/recommendations?user_id=demo_user&limit=5`);
    if (!response.ok) throw new Error('Failed to fetch suggestions');
    const data = await response.json();

    // Transform API response to frontend format
    state.suggestions = data.recommendations.map(rec => ({
        id: rec.candidate.id,
        category: rec.candidate.category,
        title: rec.candidate.title,
        preview: rec.candidate.summary,
        relevance: rec.score,
        icon: getCategoryIcon(rec.candidate.category),
        signals: rec.signals.map(s => ({ icon: getSignalIcon(s.type), text: s.description })),
        content: rec.candidate
    }));
}

function getCategoryIcon(category) {
    const icons = {
        'learning': '📚',
        'work': '💼',
        'news': '📰',
        'health': '💪',
        'productivity': '⚡'
    };
    return icons[category.toLowerCase()] || '💡';
}

function getSignalIcon(type) {
    const icons = {
        'reading_history': '📖',
        'search_history': '🔍',
        'timing': '⏰',
        'trending': '📈',
        'notification': '🔔',
        'blocking': '⚠️',
        'match': '📊'
    };
    return icons[type] || '•';
}

function setupEventListeners() {
    // Chat form submission
    chatForm.addEventListener('submit', handleSendMessage);

    // Search form submission
    searchForm.addEventListener('submit', handleSearch);

    // Toggle sidebar
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    toggleSidebar.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('open');
            sidebarOverlay.classList.toggle('active');
        } else {
            sidebar.classList.toggle('collapsed');
        }
    });

    // Close sidebar on overlay click (mobile)
    sidebarOverlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        sidebarOverlay.classList.remove('active');
    });

    // Settings modal
    settingsBtn.addEventListener('click', () => {
        updateSnoozeStatus();
        openModal(settingsModal);
    });
    document.getElementById('close-settings').addEventListener('click', () => closeModal(settingsModal));
    document.getElementById('cancel-settings').addEventListener('click', () => closeModal(settingsModal));
    document.getElementById('save-settings').addEventListener('click', saveSettings);

    // Snooze buttons
    document.querySelectorAll('.snooze-btn').forEach(btn => {
        btn.addEventListener('click', () => handleSnooze(parseInt(btn.dataset.hours)));
    });
    document.getElementById('cancel-snooze').addEventListener('click', handleCancelSnooze);

    // Transparency modal
    document.getElementById('close-transparency').addEventListener('click', () => closeModal(transparencyModal));
    document.getElementById('close-transparency-btn').addEventListener('click', () => closeModal(transparencyModal));
    document.getElementById('dont-show-like-this').addEventListener('click', handleDontShowLikeThis);

    // Clear chat history
    document.getElementById('clear-chat-history').addEventListener('click', () => {
        if (confirm('Are you sure you want to clear your chat history? This cannot be undone.')) {
            clearChatHistory();
            closeModal(settingsModal);
        }
    });

    // Theme toggle buttons
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setTheme(btn.dataset.theme);
        });
    });

    // Close modals on outside click
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target);
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('open');
            document.getElementById('sidebar-overlay').classList.remove('active');
        }
    });

    // Network status handlers
    window.addEventListener('online', () => {
        showNotification('Back online!', 'success');
        // Try to refresh suggestions
        fetchSuggestions().then(() => {
            renderSuggestionCards();
            updateNotificationBadge();
        }).catch(() => {});
    });

    window.addEventListener('offline', () => {
        showNotification('You are offline. Some features may not work.', 'warning');
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function handleKeyboardShortcuts(e) {
    // Don't trigger shortcuts when typing in input fields
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        // Escape to blur input
        if (e.key === 'Escape') {
            e.target.blur();
        }
        return;
    }

    // Check for modifier keys
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const cmdOrCtrl = isMac ? e.metaKey : e.ctrlKey;

    // Cmd/Ctrl + K: Focus search
    if (cmdOrCtrl && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
        // Open sidebar on mobile if closed
        if (window.innerWidth <= 768 && !sidebar.classList.contains('open')) {
            sidebar.classList.add('open');
            document.getElementById('sidebar-overlay').classList.add('active');
        }
        return;
    }

    // Cmd/Ctrl + /: Focus message input
    if (cmdOrCtrl && e.key === '/') {
        e.preventDefault();
        messageInput.focus();
        return;
    }

    // Cmd/Ctrl + ,: Open settings
    if (cmdOrCtrl && e.key === ',') {
        e.preventDefault();
        updateSnoozeStatus();
        openModal(settingsModal);
        return;
    }

    // Escape: Close modals
    if (e.key === 'Escape') {
        const activeModal = document.querySelector('.modal.active');
        if (activeModal) {
            closeModal(activeModal);
        }
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            document.getElementById('sidebar-overlay').classList.remove('active');
        }
        return;
    }

    // S: Toggle sidebar (when not in input)
    if (e.key === 's' && !cmdOrCtrl && !e.shiftKey) {
        e.preventDefault();
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('open');
            document.getElementById('sidebar-overlay').classList.toggle('active');
        } else {
            sidebar.classList.toggle('collapsed');
        }
        return;
    }

    // ?: Show keyboard shortcuts help
    if (e.key === '?' && e.shiftKey) {
        e.preventDefault();
        showKeyboardShortcutsHelp();
        return;
    }

    // Number keys 1-5: Start conversation with corresponding suggestion
    if (/^[1-5]$/.test(e.key) && !cmdOrCtrl) {
        const index = parseInt(e.key) - 1;
        if (state.suggestions[index]) {
            e.preventDefault();
            startConversation(state.suggestions[index]);
        }
        return;
    }
}

function showKeyboardShortcutsHelp() {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const mod = isMac ? '⌘' : 'Ctrl';

    // Remove existing help modal if present
    const existing = document.getElementById('shortcuts-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.className = 'modal active';
    modal.id = 'shortcuts-modal';
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 400px;">
            <div class="modal-header">
                <h2>Keyboard Shortcuts</h2>
                <button class="close-modal" onclick="this.closest('.modal').remove()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="shortcuts-list">
                    <div class="shortcut-item">
                        <span class="shortcut-keys">${mod} + K</span>
                        <span class="shortcut-desc">Focus search</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">${mod} + /</span>
                        <span class="shortcut-desc">Focus message input</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">${mod} + ,</span>
                        <span class="shortcut-desc">Open settings</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">S</span>
                        <span class="shortcut-desc">Toggle sidebar</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">1-5</span>
                        <span class="shortcut-desc">Start suggestion #1-5</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">Esc</span>
                        <span class="shortcut-desc">Close modal / blur input</span>
                    </div>
                    <div class="shortcut-item">
                        <span class="shortcut-keys">?</span>
                        <span class="shortcut-desc">Show this help</span>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-primary" onclick="this.closest('.modal').remove()">Got it</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

async function handleSnooze(hours) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/snooze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'demo_user',
                hours: hours
            })
        });

        if (response.ok) {
            const data = await response.json();
            state.snoozedUntil = data.until;
            localStorage.setItem('proactive_ai_snoozed_until', data.until);
            updateSnoozeStatus();
            addMessage('assistant', `Got it! I'll pause notifications for ${hours} hour${hours > 1 ? 's' : ''}. You can resume anytime in settings.`);
        }
    } catch (error) {
        console.error('Failed to snooze:', error);
        // Store locally as fallback
        const until = new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
        state.snoozedUntil = until;
        localStorage.setItem('proactive_ai_snoozed_until', until);
        updateSnoozeStatus();
    }
}

async function handleCancelSnooze() {
    try {
        await fetch(`${API_BASE_URL}/api/snooze/demo_user`, {
            method: 'DELETE'
        });
    } catch (error) {
        console.error('Failed to cancel snooze:', error);
    }

    state.snoozedUntil = null;
    localStorage.removeItem('proactive_ai_snoozed_until');
    updateSnoozeStatus();
    addMessage('assistant', 'Notifications resumed! I\'ll start suggesting relevant topics again.');
}

function updateSnoozeStatus() {
    const statusEl = document.getElementById('snooze-status');
    const cancelBtn = document.getElementById('cancel-snooze');

    // Check localStorage for snooze status
    const snoozedUntil = localStorage.getItem('proactive_ai_snoozed_until');

    if (snoozedUntil) {
        const until = new Date(snoozedUntil);
        if (until > new Date()) {
            const timeLeft = formatTimeLeft(until);
            statusEl.textContent = `Notifications snoozed for ${timeLeft}`;
            statusEl.classList.add('snoozed');
            cancelBtn.style.display = 'block';
            return;
        } else {
            // Snooze expired
            localStorage.removeItem('proactive_ai_snoozed_until');
        }
    }

    statusEl.textContent = 'Notifications are active';
    statusEl.classList.remove('snoozed');
    cancelBtn.style.display = 'none';
}

function formatTimeLeft(until) {
    const diff = until - new Date();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) {
        const days = Math.floor(hours / 24);
        return `${days} day${days > 1 ? 's' : ''}`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes} minutes`;
    }
}

async function handleSendMessage(e) {
    e.preventDefault();
    const rawMessage = messageInput.value;
    const message = sanitizeInput(rawMessage);

    // Validate message
    const validation = validateMessageLength(message);
    if (!validation.valid) {
        showNotification(validation.error, 'error');
        return;
    }

    // Add user message
    addMessage('user', message);
    messageInput.value = '';
    sendBtn.disabled = true;

    // Try streaming first, fall back to regular API
    try {
        await handleStreamingResponse(message);
    } catch (error) {
        console.error('Streaming failed:', error);
        // Fall back to non-streaming API
        try {
            await handleRegularResponse(message);
        } catch (fallbackError) {
            console.error('Regular API also failed:', fallbackError);
            // Check if it's a network error
            if (!navigator.onLine) {
                showNotification('No internet connection. Please check your network.', 'error');
                addMessage('assistant', "I'm having trouble connecting to the server. Please check your internet connection and try again.");
            } else {
                // Mock response for demo
                const mockResponse = generateMockResponse(message);
                addMessage('assistant', mockResponse);
            }
        }
    }

    sendBtn.disabled = false;
}

async function handleStreamingResponse(message) {
    // Create message element for streaming
    const messageDiv = createStreamingMessage();

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: 'demo_user',
            message: message,
            context: state.currentSuggestion ? {
                suggestion_id: state.currentSuggestion.id,
                topic: state.currentSuggestion.content.title
            } : null
        })
    });

    if (!response.ok) throw new Error('Stream request failed');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    let streamComplete = false;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        // Parse SSE format
        const lines = chunk.split('\n');
        for (const line of lines) {
            // Check for data: prefix (with or without space after colon)
            if (line.startsWith('data:')) {
                // Extract data after "data:" - handle both "data: x" and "data:x"
                const data = line.startsWith('data: ') ? line.slice(6) : line.slice(5);

                if (data === '[DONE]') {
                    streamComplete = true;
                    break;
                } else if (data.startsWith('[ERROR:')) {
                    throw new Error(data);
                } else {
                    // Decode escaped newlines back to real newlines
                    const decodedData = data.replace(/\\n/g, '\n');
                    fullContent += decodedData;
                    updateStreamingMessage(messageDiv, fullContent);
                }
            }
        }

        if (streamComplete) break;
    }

    // Finalize the message
    finalizeStreamingMessage(messageDiv, fullContent);
    state.messages.push({ role: 'assistant', content: fullContent });
    saveMessages();
}

async function handleRegularResponse(message) {
    // Show typing indicator
    showTypingIndicator();

    const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: 'demo_user',
            message: message,
            context: state.currentSuggestion ? {
                suggestion_id: state.currentSuggestion.id,
                topic: state.currentSuggestion.content.title
            } : null
        })
    });

    if (!response.ok) throw new Error('Chat failed');
    const data = await response.json();

    hideTypingIndicator();
    addMessage('assistant', data.response);
}

function createStreamingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant streaming';
    messageDiv.id = 'streaming-message';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = 'AI';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const streamingDiv = document.createElement('div');
    streamingDiv.className = 'streaming-text';
    streamingDiv.innerHTML = '<span class="cursor">▊</span>';
    contentDiv.appendChild(streamingDiv);

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

function updateStreamingMessage(messageDiv, content) {
    const streamingDiv = messageDiv.querySelector('.streaming-text');
    // Show plain text content with cursor at end during streaming
    streamingDiv.innerHTML = escapeHtml(content) + '<span class="cursor">▊</span>';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function finalizeStreamingMessage(messageDiv, content) {
    const contentDiv = messageDiv.querySelector('.message-content');
    const streamingDiv = messageDiv.querySelector('.streaming-text');

    // Replace streaming div with rendered markdown
    const markdownDiv = document.createElement('div');
    markdownDiv.className = 'markdown-content';
    markdownDiv.innerHTML = renderMarkdown(content);

    contentDiv.replaceChild(markdownDiv, streamingDiv);
    messageDiv.classList.remove('streaming');
    messageDiv.removeAttribute('id');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function generateMockResponse(userMessage) {
    const responses = [
        "That's a great question! Let me explain this concept in more detail.",
        "I understand what you're asking. Here's what I think would be most helpful...",
        "Based on your interests, I'd recommend focusing on the practical applications first.",
        "This connects well with what you've been learning about distributed systems.",
        "Would you like me to break this down into smaller, more manageable topics?"
    ];
    return responses[Math.floor(Math.random() * responses.length)];
}

function addMessage(role, content, metadata = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = role === 'assistant' ? 'AI' : 'You';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Render markdown for assistant messages, plain text for user
    if (role === 'assistant') {
        const markdownDiv = document.createElement('div');
        markdownDiv.className = 'markdown-content';
        markdownDiv.innerHTML = renderMarkdown(content);
        contentDiv.appendChild(markdownDiv);
    } else {
        const textP = document.createElement('p');
        textP.textContent = content;
        contentDiv.appendChild(textP);
    }

    if (metadata && metadata.basedOn) {
        const basedOnDiv = document.createElement('div');
        basedOnDiv.className = 'based-on';
        basedOnDiv.innerHTML = `📚 Based on: ${metadata.basedOn}`;
        contentDiv.appendChild(basedOnDiv);
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    state.messages.push({ role, content, metadata });
    saveMessages();
}

function renderMarkdown(content) {
    // Try marked.js if available (handle different versions)
    if (typeof marked !== 'undefined') {
        try {
            let result;
            const options = { breaks: true, gfm: true };

            // Try different API patterns for different marked versions
            if (typeof marked.parse === 'function') {
                result = marked.parse(content, options);
            } else if (typeof marked === 'function') {
                result = marked(content, options);
            } else if (typeof marked.marked === 'function') {
                result = marked.marked(content, options);
            }

            if (result) {
                return result;
            }
        } catch (e) {
            // Fall through to fallback renderer
        }
    }

    // Fallback: simple markdown rendering
    return simpleMarkdown(content);
}

function simpleMarkdown(text) {
    // Basic markdown rendering fallback
    if (!text) return '';

    let html = text;

    // First, protect code blocks by replacing them with placeholders
    const codeBlocks = [];
    html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, function(match, lang, code) {
        const index = codeBlocks.length;
        codeBlocks.push('<pre><code>' + escapeHtml(code.trim()) + '</code></pre>');
        return `__CODE_BLOCK_${index}__`;
    });

    // Protect inline code
    const inlineCodes = [];
    html = html.replace(/`([^`]+)`/g, function(match, code) {
        const index = inlineCodes.length;
        inlineCodes.push('<code>' + escapeHtml(code) + '</code>');
        return `__INLINE_CODE_${index}__`;
    });

    // Escape remaining HTML
    html = escapeHtml(html);

    // Restore code blocks and inline code
    codeBlocks.forEach((block, i) => {
        html = html.replace(`__CODE_BLOCK_${i}__`, block);
    });
    inlineCodes.forEach((code, i) => {
        html = html.replace(`__INLINE_CODE_${i}__`, code);
    });

    // Bold (**...**) - must come before italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic (*...*) - single asterisks only (bold already processed)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Headers (must be at start of line)
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Unordered lists - convert lines starting with -
    const lines = html.split('\n');
    let inList = false;
    const processedLines = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const listMatch = line.match(/^- (.+)$/);

        if (listMatch) {
            if (!inList) {
                processedLines.push('<ul>');
                inList = true;
            }
            processedLines.push('<li>' + listMatch[1] + '</li>');
        } else {
            if (inList) {
                processedLines.push('</ul>');
                inList = false;
            }
            processedLines.push(line);
        }
    }
    if (inList) {
        processedLines.push('</ul>');
    }
    html = processedLines.join('\n');

    // Convert remaining newlines to <br>, but not inside block elements
    html = html.replace(/\n/g, '<br>\n');

    // Clean up extra <br> after/before block elements
    html = html.replace(/<br>\n?<\/(ul|ol|pre|h[1-6])>/g, '</$1>');
    html = html.replace(/<(ul|ol|pre|h[1-6])><br>\n?/g, '<$1>');
    html = html.replace(/<\/(ul|ol|pre|li|h[1-6])><br>/g, '</$1>');
    html = html.replace(/<\/li><br>\n?<li>/g, '</li><li>');

    return html;
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">AI</div>
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function renderSuggestionCards() {
    suggestionCards.innerHTML = '';

    if (state.suggestions.length === 0) {
        suggestionCards.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">&#128161;</div>
                <div class="empty-state-title">No suggestions yet</div>
                <div class="empty-state-description">Check back later for personalized recommendations based on your interests.</div>
            </div>
        `;
        return;
    }

    state.suggestions.forEach(suggestion => {
        const card = createSuggestionCard(suggestion);
        suggestionCards.appendChild(card);
    });
}

function showSuggestionSkeletons(count = 3) {
    suggestionCards.innerHTML = '';
    for (let i = 0; i < count; i++) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-card';
        skeleton.innerHTML = `
            <div class="skeleton skeleton-icon"></div>
            <div class="skeleton skeleton-category"></div>
            <div class="skeleton skeleton-title"></div>
            <div class="skeleton skeleton-preview"></div>
            <div class="skeleton skeleton-preview-short"></div>
            <div class="skeleton-meta">
                <div class="skeleton skeleton-meta-text"></div>
                <div class="skeleton skeleton-bar"></div>
                <div class="skeleton skeleton-meta-percent"></div>
            </div>
        `;
        suggestionCards.appendChild(skeleton);
    }
}

function createSuggestionCard(suggestion) {
    const card = document.createElement('div');
    card.className = 'suggestion-card';
    card.setAttribute('data-title', suggestion.title);
    card.innerHTML = `
        <div class="card-icon">${suggestion.icon}</div>
        <div class="card-category">${suggestion.category}</div>
        <div class="card-title">${suggestion.title}</div>
        <div class="card-preview">${suggestion.preview}</div>
        <div class="card-meta">
            <span>Relevance:</span>
            <div class="relevance-bar">
                <div class="relevance-fill" style="width: ${suggestion.relevance * 100}%"></div>
            </div>
            <span>${Math.round(suggestion.relevance * 100)}%</span>
        </div>
        <div class="card-actions">
            <button class="btn-start" data-id="${suggestion.id}">Start</button>
            <button class="btn-later" data-id="${suggestion.id}">Later</button>
            <button class="btn-why" data-id="${suggestion.id}">Why?</button>
        </div>
    `;

    // Event listeners
    card.querySelector('.btn-start').addEventListener('click', (e) => {
        e.stopPropagation();
        startConversation(suggestion);
    });

    card.querySelector('.btn-later').addEventListener('click', (e) => {
        e.stopPropagation();
        dismissSuggestion(suggestion.id, 'later');
    });

    card.querySelector('.btn-why').addEventListener('click', (e) => {
        e.stopPropagation();
        showTransparencyPanel(suggestion);
    });

    return card;
}

async function startConversation(suggestion) {
    state.currentSuggestion = suggestion;

    // Remove from suggestions immediately
    state.suggestions = state.suggestions.filter(s => s.id !== suggestion.id);
    renderSuggestionCards();
    updateNotificationBadge();

    // Record feedback
    recordFeedback(suggestion.id, 'started');

    // Generate proactive intro using the model
    try {
        await generateProactiveIntro(suggestion);
    } catch (error) {
        // Fallback to static message if API fails
        const fallbackMessage = `I noticed you've been ${getInterestDescription(suggestion)}. ${suggestion.title} It connects well with what you're learning.`;
        addMessage('assistant', fallbackMessage, { basedOn: suggestion.preview });
    }
}

async function generateProactiveIntro(suggestion) {
    // Create message element for streaming
    const messageDiv = createStreamingMessage();

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: 'demo_user',
            message: '__PROACTIVE_INTRO__',  // Special marker for proactive intro
            context: {
                type: 'proactive_intro',
                suggestion_id: suggestion.id,
                title: suggestion.content?.title || suggestion.title,
                summary: suggestion.content?.summary || suggestion.preview,
                category: suggestion.category,
                signals: suggestion.signals
            }
        })
    });

    if (!response.ok) throw new Error('Stream request failed');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    let streamComplete = false;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data:')) {
                const data = line.startsWith('data: ') ? line.slice(6) : line.slice(5);

                if (data === '[DONE]') {
                    streamComplete = true;
                    break;
                } else if (data.startsWith('[ERROR:')) {
                    throw new Error(data);
                } else {
                    const decodedData = data.replace(/\\n/g, '\n');
                    fullContent += decodedData;
                    updateStreamingMessage(messageDiv, fullContent);
                }
            }
        }

        if (streamComplete) break;
    }

    // Finalize the message
    finalizeStreamingMessage(messageDiv, fullContent);
    state.messages.push({ role: 'assistant', content: fullContent });
    saveMessages();
}

function getInterestDescription(suggestion) {
    const category = suggestion.category.toLowerCase();
    const descriptions = {
        'learning': 'diving deep into technical topics',
        'work': 'working on important pull requests',
        'news': 'interested in industry developments',
        'health': 'focusing on your wellbeing',
        'productivity': 'optimizing your workflow'
    };
    return descriptions[category] || 'exploring new areas';
}

function dismissSuggestion(id, reason) {
    state.suggestions = state.suggestions.filter(s => s.id !== id);
    renderSuggestionCards();
    updateNotificationBadge();
    recordFeedback(id, reason === 'later' ? 'dismissed' : 'rejected');
}

function showTransparencyPanel(suggestion) {
    const body = document.getElementById('transparency-body');
    body.innerHTML = `
        <p style="margin-bottom: 16px; color: var(--text-secondary);">Signals used for this suggestion:</p>
        <ul class="signals-list">
            ${suggestion.signals.map(s => `
                <li>
                    <span class="signal-icon">${s.icon}</span>
                    <span>${s.text}</span>
                </li>
            `).join('')}
        </ul>
    `;

    state.currentSuggestion = suggestion;
    openModal(transparencyModal);
}

function handleDontShowLikeThis() {
    if (state.currentSuggestion) {
        dismissSuggestion(state.currentSuggestion.id, 'rejected');
        recordFeedback(state.currentSuggestion.id, 'dont_show_like_this');
    }
    closeModal(transparencyModal);
}

function updateNotificationBadge() {
    const count = state.suggestions.length;

    notificationBadge.classList.remove('has-suggestion', 'high-relevance', 'urgent');

    if (count === 0) return;

    const maxRelevance = Math.max(...state.suggestions.map(s => s.relevance));

    if (maxRelevance >= 0.9) {
        notificationBadge.classList.add('urgent');
    } else if (maxRelevance >= 0.8) {
        notificationBadge.classList.add('high-relevance');
    } else {
        notificationBadge.classList.add('has-suggestion');
    }
}

function renderQuickActions() {
    quickActions.innerHTML = '';

    const actions = [
        { label: 'Tell me more', value: 'tell me more about this topic' },
        { label: 'Show examples', value: 'can you show me some examples?' },
        { label: 'Simplify', value: 'can you explain this more simply?' },
        { label: 'Next steps', value: 'what should I learn next?' }
    ];

    actions.forEach(action => {
        const btn = document.createElement('button');
        btn.className = 'quick-action-btn';
        btn.textContent = action.label;
        btn.addEventListener('click', () => {
            messageInput.value = action.value;
            chatForm.dispatchEvent(new Event('submit'));
        });
        quickActions.appendChild(btn);
    });
}

async function recordFeedback(suggestionId, action) {
    try {
        await fetch(`${API_BASE_URL}/api/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'demo_user',
                candidate_id: suggestionId,
                action: action,
                conversation_turns: state.messages.length
            })
        });
    } catch (error) {
        console.error('Failed to record feedback:', error);
    }
}

// Notification system for user feedback
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification-toast');
    if (existing) existing.remove();

    const notification = document.createElement('div');
    notification.className = `notification-toast notification-${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Trigger animation
    setTimeout(() => notification.classList.add('show'), 10);

    // Auto-dismiss after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Search functionality
async function handleSearch(e) {
    e.preventDefault();
    const rawQuery = searchInput.value;
    const query = sanitizeInput(rawQuery);

    const validation = validateSearchQuery(query);
    if (!validation.valid) {
        showNotification(validation.error, 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                user_id: 'demo_user',
                limit: 5
            })
        });

        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();
        renderSearchResults(data);
    } catch (error) {
        console.error('Search error:', error);
        showNotification('Search failed. Please try again.', 'error');
    }
}

function renderSearchResults(data) {
    const results = data.results || [];
    const expandedTerms = data.expanded_terms || [];

    if (results.length === 0) {
        searchResults.innerHTML = `
            <div class="search-results-header">
                <span class="search-results-title">No results found</span>
                <button class="search-clear-btn" onclick="clearSearchResults()">Clear</button>
            </div>
            <div class="search-no-results">Try different keywords or check your spelling.</div>
        `;
    } else {
        searchResults.innerHTML = `
            <div class="search-results-header">
                <span class="search-results-title">${results.length} result${results.length !== 1 ? 's' : ''}</span>
                <button class="search-clear-btn" onclick="clearSearchResults()">Clear</button>
            </div>
            ${expandedTerms.length > 0 ? `
                <div class="search-expanded-terms">
                    ${expandedTerms.map(term => `<span class="expanded-term">${term}</span>`).join('')}
                </div>
            ` : ''}
            ${results.map(result => `
                <div class="search-result-card" onclick="startConversationFromSearch('${result.candidate.id}')">
                    <div class="search-result-title">${escapeHtml(result.candidate.title)}</div>
                    <div class="search-result-summary">${escapeHtml(result.candidate.summary)}</div>
                    <div class="search-result-score">Relevance: ${Math.round(result.score * 100)}%</div>
                </div>
            `).join('')}
        `;
    }

    searchResults.classList.add('active');
}

function clearSearchResults() {
    searchResults.innerHTML = '';
    searchResults.classList.remove('active');
    searchInput.value = '';
}

function startConversationFromSearch(candidateId) {
    // Find the candidate in suggestions or fetch it
    const suggestion = state.suggestions.find(s => s.id === candidateId);
    if (suggestion) {
        startConversation(suggestion);
        clearSearchResults();
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('open');
            document.getElementById('sidebar-overlay').classList.remove('active');
        }
    }
}

function openModal(modal) {
    modal.classList.add('active');
}

function closeModal(modal) {
    modal.classList.remove('active');
}

function saveSettings() {
    // Collect settings from form
    const frequency = document.querySelector('input[name="frequency"]:checked').value;

    state.settings = {
        frequency,
        pauseMeetings: document.getElementById('pause-meetings').checked,
        detectDeepWork: document.getElementById('detect-deep-work').checked,
        queueOnly: document.getElementById('queue-only').checked
    };

    // Save to API
    saveSettingsToAPI(state.settings);
    closeModal(settingsModal);
}

async function saveSettingsToAPI(settings) {
    try {
        await fetch(`${API_BASE_URL}/api/preferences`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: 'demo_user',
                ...settings
            })
        });
    } catch (error) {
        console.error('Failed to save settings:', error);
    }
}
