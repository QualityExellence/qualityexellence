// Main Application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initApp();

    // Check if user is logged in
    if (!isLoggedIn()) {
        showLoginModal();
    }
});

// Global variables
let currentUser = null;
let apiBaseUrl = '/api';
let chartInstances = {};
let uploadedFile = null;

// Initialize the application
function initApp() {
    // Setup event listeners
    setupSidebar();
    setupNavigation();
    setupUploadArea();
    setupModals();
    setupForms();
    setupDashboard();

    // Load user data if logged in
    if (isLoggedIn()) {
        loadUserData();
        loadRecordings();
    }
}

// Check if user is logged in
function isLoggedIn() {
    return localStorage.getItem('access_token') !== null;
}

const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    // Obter token do localStorage
    const token = localStorage.getItem('token');

    // Se tiver token e não for uma requisição de login ou registro
    if (token && !url.includes('/api/auth/login') && !url.includes('/api/auth/register')) {
        // Criar ou atualizar headers
        options.headers = options.headers || {};
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    // Chamar fetch original
    return originalFetch(url, options);
};

// Verificar token ao carregar a página
document.addEventListener('DOMContentLoaded', function() {
    // Resto do código...
});

// Setup sidebar functionality
function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');

    sidebarToggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');

        // On mobile, add overlay when sidebar is expanded
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('expanded');

            const overlay = document.createElement('div');
            overlay.classList.add('overlay');

            if (sidebar.classList.contains('expanded')) {
                document.body.appendChild(overlay);
                overlay.classList.add('active');

                overlay.addEventListener('click', function() {
                    sidebar.classList.remove('expanded');
                    overlay.remove();
                });
            } else {
                const existingOverlay = document.querySelector('.overlay');
                if (existingOverlay) {
                    existingOverlay.remove();
                }
            }
        }
    });

    // Auto-collapse sidebar on mobile
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }

    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth <= 768) {
            sidebar.classList.add('collapsed');
            sidebar.classList.remove('expanded');

            const existingOverlay = document.querySelector('.overlay');
            if (existingOverlay) {
                existingOverlay.remove();
            }
        }
    });
}

// Setup navigation between pages
function setupNavigation() {
    const navLinks = document.querySelectorAll('.sidebar-menu a');
    const contentPages = document.querySelectorAll('.content-page');
    const pageTitle = document.getElementById('page-title');

    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();

            // Update active link
            navLinks.forEach(l => l.parentElement.classList.remove('active'));
            this.parentElement.classList.add('active');

            // Show corresponding page
            const targetPage = this.getAttribute('data-page');
            contentPages.forEach(page => {
                page.classList.remove('active');
                if (page.id === `${targetPage}-page`) {
                    page.classList.add('active');
                    pageTitle.textContent = this.querySelector('span').textContent;
                }
            });

            // On mobile, collapse sidebar after navigation
            if (window.innerWidth <= 768) {
                const sidebar = document.getElementById('sidebar');
                sidebar.classList.remove('expanded');

                const existingOverlay = document.querySelector('.overlay');
                if (existingOverlay) {
                    existingOverlay.remove();
                }
            }

            // Load page-specific data
            if (targetPage === 'dashboard') {
                loadDashboardData();
            } else if (targetPage === 'transcriptions') {
                loadTranscriptions();
            }
        });
    });
}

// Setup upload area functionality
function setupUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const selectFileBtn = document.getElementById('select-file-btn');
    const uploadProgress = document.getElementById('upload-progress');
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    const fileName = document.querySelector('.file-name');
    const cancelUploadBtn = document.getElementById('cancel-upload-btn');
    const uploadSuccess = document.getElementById('upload-success');
    const transcribeBtn = document.getElementById('transcribe-btn');
    const uploadAnotherBtn = document.getElementById('upload-another-btn');

    // Click on upload area to select file
    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });

    // Click on select file button
    selectFileBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const file = this.files[0];
            uploadedFile = file;

            // Check file type
            const fileType = file.name.split('.').pop().toLowerCase();
            if (!['mp3', 'mp4', 'wav', 'webm'].includes(fileType)) {
                alert('Formato de arquivo não suportado. Use: mp3, mp4, wav, webm');
                return;
            }

            // Show progress
            uploadArea.style.display = 'none';
            uploadProgress.style.display = 'block';
            fileName.textContent = file.name;

            // Create FormData and upload file
            const formData = new FormData();
            formData.append('file', file);

            // Upload file to server
            uploadFile(formData, progressFill, progressText, uploadProgress, uploadSuccess);
        }
    });

    // Cancel upload
    cancelUploadBtn.addEventListener('click', function() {
        // If there's an ongoing upload, abort it
        if (window.currentUpload) {
            window.currentUpload.abort();
        }

        uploadProgress.style.display = 'none';
        uploadArea.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        fileInput.value = '';
        uploadedFile = null;
    });

    // Transcribe button
    transcribeBtn.addEventListener('click', function() {
        if (!uploadedFile) {
            alert('Nenhum arquivo disponível para transcrição');
            return;
        }

        // Get the recording ID from the last upload
        const recordingId = localStorage.getItem('last_uploaded_recording_id');
        if (!recordingId) {
            alert('ID da gravação não encontrado. Tente fazer o upload novamente.');
            return;
        }

        // Show loading state
        transcribeBtn.disabled = true;
        transcribeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Transcrevendo...';

        // Call transcribe API
        transcribeRecording(recordingId)
            .then(response => {
                // Navigate to transcriptions page
                const transcriptionsLink = document.querySelector('.sidebar-menu a[data-page="transcriptions"]');
                if (transcriptionsLink) {
                    transcriptionsLink.click();
                }

                // Reset upload area
                uploadSuccess.style.display = 'none';
                uploadArea.style.display = 'block';
                fileInput.value = '';
                uploadedFile = null;

                // Show success message
                showNotification('Transcrição iniciada com sucesso!', 'success');
            })
            .catch(error => {
                console.error('Erro ao transcrever:', error);
                showNotification('Erro ao iniciar transcrição. Tente novamente.', 'error');
            })
            .finally(() => {
                // Reset button state
                transcribeBtn.disabled = false;
                transcribeBtn.innerHTML = 'Transcrever Agora';
            });
    });

    // Upload another button
    uploadAnotherBtn.addEventListener('click', function() {
        uploadSuccess.style.display = 'none';
        uploadArea.style.display = 'block';
        fileInput.value = '';
        uploadedFile = null;
    });

    // Import button
    const importBtn = document.getElementById('import-btn');
    importBtn.addEventListener('click', function() {
        // Get filter values
        const startDate = document.getElementById('start-date').value;
        const endDate = document.getElementById('end-date').value;
        const operator = document.getElementById('operator-filter').value;

        if (!startDate || !endDate) {
            alert('Por favor, selecione as datas inicial e final');
            return;
        }

        // Show loading state
        importBtn.disabled = true;
        importBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importando...';

        // Call import API
        importRecordings(startDate, endDate, operator)
            .then(response => {
                // Reload recordings
                loadRecordings();

                // Show success message
                showNotification('Gravações importadas com sucesso!', 'success');
            })
            .catch(error => {
                console.error('Erro ao importar:', error);
                showNotification('Erro ao importar gravações. Tente novamente.', 'error');
            })
            .finally(() => {
                // Reset button state
                importBtn.disabled = false;
                importBtn.innerHTML = 'Importar Gravações';
            });
    });
}

// Upload file to server
function uploadFile(formData, progressFill, progressText, uploadProgress, uploadSuccess) {
    const xhr = new XMLHttpRequest();
    window.currentUpload = xhr;

    xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
            const percentComplete = Math.round((e.loaded / e.total) * 100);
            progressFill.style.width = percentComplete + '%';
            progressText.textContent = percentComplete + '%';
        }
    });

    xhr.addEventListener('load', function() {
        if (xhr.status === 200 || xhr.status === 201) {
            const response = JSON.parse(xhr.responseText);

            // Store recording ID for later use
            if (response.id) {
                localStorage.setItem('last_uploaded_recording_id', response.id);
            }

            // Show success after a short delay
            setTimeout(function() {
                uploadProgress.style.display = 'none';
                uploadSuccess.style.display = 'block';
            }, 500);

            // Reload recordings
            loadRecordings();
        } else {
            console.error('Upload failed:', xhr.responseText);
            showNotification('Erro ao fazer upload. Tente novamente.', 'error');

            // Reset upload area
            uploadProgress.style.display = 'none';
            document.getElementById('upload-area').style.display = 'block';
        }
    });

    xhr.addEventListener('error', function() {
        console.error('Upload failed');
        showNotification('Erro ao fazer upload. Tente novamente.', 'error');

        // Reset upload area
        uploadProgress.style.display = 'none';
        document.getElementById('upload-area').style.display = 'block';
    });

    xhr.addEventListener('abort', function() {
        console.log('Upload aborted');
        showNotification('Upload cancelado', 'info');
    });

    xhr.open('POST', apiBaseUrl + '/upload/upload', true);

    // Add authorization header if logged in
    const token = localStorage.getItem('access_token');
    if (token) {
        xhr.setRequestHeader('Authorization', 'Bearer ' + token);
    }

    xhr.send(formData);
}

// Transcribe recording
async function transcribeRecording(recordingId) {
    try {
        const response = await fetch(`${apiBaseUrl}/transcription/transcribe/${recordingId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao transcrever gravação');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao transcrever:', error);
        throw error;
    }
}

// Import recordings from 4COM
async function importRecordings(startDate, endDate, operator) {
    try {
        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate
        });

        if (operator) {
            params.append('operator', operator);
        }

        const response = await fetch(`${apiBaseUrl}/fourcom/import?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao importar gravações');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao importar:', error);
        throw error;
    }
}

// Setup modals
function setupModals() {
    // Transcription modal
    const viewTranscriptionBtns = document.querySelectorAll('.view-transcription-btn');
    const transcriptionModal = document.getElementById('transcription-modal');
    const closeModalBtns = document.querySelectorAll('.close-modal');

    viewTranscriptionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-id');
            loadTranscriptionDetails(transcriptionId)
                .then(data => {
                    // Update modal with transcription details
                    updateTranscriptionModal(data);

                    // Show modal
                    transcriptionModal.classList.add('active');
                })
                .catch(error => {
                    console.error('Erro ao carregar detalhes da transcrição:', error);
                    showNotification('Erro ao carregar detalhes da transcrição', 'error');
                });
        });
    });

    // Close modals
    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            modal.classList.remove('active');
        });
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal') && e.target.classList.contains('active')) {
            e.target.classList.remove('active');
        }
    });

    // Register link
    const registerLink = document.getElementById('register-link');
    const registerModal = document.getElementById('register-modal');
    const loginModal = document.getElementById('login-modal');

    registerLink.addEventListener('click', function(e) {
        e.preventDefault();
        loginModal.classList.remove('active');
        registerModal.classList.add('active');
    });

    // Login link
    const loginLink = document.getElementById('login-link');

    loginLink.addEventListener('click', function(e) {
        e.preventDefault();
        registerModal.classList.remove('active');
        loginModal.classList.add('active');
    });

    // Export PDF button
    const exportPdfBtn = document.getElementById('export-pdf-btn');

    exportPdfBtn.addEventListener('click', function() {
        const transcriptionId = this.closest('.modal').getAttribute('data-transcription-id');
        if (!transcriptionId) {
            alert('ID da transcrição não encontrado');
            return;
        }

        // Export PDF
        window.open(`${apiBaseUrl}/export/pdf/${transcriptionId}`, '_blank');
    });

    // Export CSV button
    const exportCsvBtn = document.getElementById('export-csv-btn');

    exportCsvBtn.addEventListener('click', function() {
        const transcriptionId = this.closest('.modal').getAttribute('data-transcription-id');
        if (!transcriptionId) {
            alert('ID da transcrição não encontrado');
            return;
        }

        // Export CSV
        window.open(`${apiBaseUrl}/export/csv/${transcriptionId}`, '_blank');
    });
}

// Update transcription modal with data
function updateTranscriptionModal(data) {
    // Set transcription ID
    document.getElementById('transcription-modal').setAttribute('data-transcription-id', data.id);

    // Update header
    document.getElementById('transcription-title').textContent = data.title || 'Transcrição';
    document.getElementById('transcription-date').textContent = formatDate(data.created_at);
    document.getElementById('transcription-duration').textContent = formatDuration(data.duration);
    document.getElementById('transcription-operator').textContent = data.operator || 'Não especificado';

    // Update summary
    document.getElementById('transcription-summary-text').textContent = data.summary || 'Resumo não disponível';

    // Update sentiment
    const sentimentValue = data.sentiment_score || 0.5;
    const sentimentPosition = (sentimentValue + 1) / 2 * 100; // Convert -1...1 to 0...100
    document.getElementById('sentiment-indicator').style.left = `${sentimentPosition}%`;

    // Update keywords
    const keywordsCloud = document.getElementById('keywords-cloud');
    keywordsCloud.innerHTML = '';

    if (data.keywords && data.keywords.length > 0) {
        data.keywords.forEach(keyword => {
            const fontSize = 0.8 + (keyword.count / 5) * 0.6; // Scale font size based on count
            const span = document.createElement('span');
            span.className = 'keyword';
            span.style.fontSize = `${fontSize}em`;
            span.textContent = `${keyword.text} (${keyword.count})`;
            keywordsCloud.appendChild(span);
        });
    } else {
        const span = document.createElement('span');
        span.className = 'keyword';
        span.textContent = 'Nenhuma palavra-chave encontrada';
        keywordsCloud.appendChild(span);
    }

    // Update segments
    const segmentsContainer = document.getElementById('transcription-segments');
    segmentsContainer.innerHTML = '';

    if (data.segments && data.segments.length > 0) {
        data.segments.forEach(segment => {
            const segmentDiv = document.createElement('div');
            segmentDiv.className = 'segment';

            const headerDiv = document.createElement('div');
            headerDiv.className = 'segment-header';

            const speakerSpan = document.createElement('span');
            speakerSpan.className = `speaker ${segment.speaker.toLowerCase()}`;
            speakerSpan.textContent = segment.speaker;
            headerDiv.appendChild(speakerSpan);

            const timestampSpan = document.createElement('span');
            timestampSpan.className = 'timestamp';
            timestampSpan.textContent = formatTimestamp(segment.start_time) + ' - ' + formatTimestamp(segment.end_time);
            headerDiv.appendChild(timestampSpan);

            const sentimentSpan = document.createElement('span');
            sentimentSpan.className = `sentiment ${getSentimentClass(segment.sentiment)}`;
            sentimentSpan.textContent = getSentimentText(segment.sentiment);
            headerDiv.appendChild(sentimentSpan);

            segmentDiv.appendChild(headerDiv);

            const textDiv = document.createElement('div');
            textDiv.className = 'segment-text';
            textDiv.textContent = segment.text;
            segmentDiv.appendChild(textDiv);

            segmentsContainer.appendChild(segmentDiv);
        });
    } else {
        const noSegmentsDiv = document.createElement('div');
        noSegmentsDiv.className = 'segment';
        noSegmentsDiv.textContent = 'Nenhum segmento de transcrição disponível';
        segmentsContainer.appendChild(noSegmentsDiv);
    }
}

// Get sentiment class based on value
function getSentimentClass(sentiment) {
    if (sentiment >= 0.3) return 'positive';
    if (sentiment <= -0.3) return 'negative';
    return 'neutral';
}

// Get sentiment text based on value
function getSentimentText(sentiment) {
    if (sentiment >= 0.3) return 'Positivo';
    if (sentiment <= -0.3) return 'Negativo';
    return 'Neutro';
}

// Format timestamp (seconds to MM:SS)
function formatTimestamp(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Format duration (seconds to MM:SS)
function formatDuration(seconds) {
    if (!seconds) return '00:00';
    return formatTimestamp(seconds);
}

// Format date (ISO to DD/MM/YYYY)
function formatDate(isoDate) {
    if (!isoDate) return '';
    const date = new Date(isoDate);
    return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getFullYear()}`;
}

// Setup forms
function setupForms() {
    // Login form
    const loginForm = document.getElementById('login-form');

    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;

        // Show loading state
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Entrando...';

        // Call login API
        login(email, password)
            .then(data => {
                // Store token and user data
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));

                // Close login modal
                document.getElementById('login-modal').classList.remove('active');

                // Update UI
                loadUserData();
                loadRecordings();

                // Show success message
                showNotification('Login realizado com sucesso!', 'success');
            })
            .catch(error => {
                console.error('Erro ao fazer login:', error);
                showNotification('Erro ao fazer login. Verifique suas credenciais.', 'error');
            })
            .finally(() => {
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.textContent = 'Entrar';
            });
    });

    // Register form
    const registerForm = document.getElementById('register-form');

    registerForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const name = document.getElementById('register-name').value;
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const passwordConfirm = document.getElementById('register-password-confirm').value;

        // Check if passwords match
        if (password !== passwordConfirm) {
            showNotification('As senhas não coincidem', 'error');
            return;
        }

        // Show loading state
        const submitBtn = registerForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Criando conta...';

        // Call register API
    function checkAuth() {
        const token = localStorage.getItem('token');
        if (!token) {
        // Redirecionar para a página de login em vez de exibir o modal
        window.location.href = '/login';
        return false;
    }
    return true;
    }
    });

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');

    logoutBtn.addEventListener('click', function() {
        // Clear local storage
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('last_uploaded_recording_id');

        // Show login modal
        showLoginModal();

        // Show success message
        showNotification('Logout realizado com sucesso!', 'success');
    });

    // Profile form
    const profileForm = document.getElementById('profile-form');

    profileForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const name = document.getElementById('user-name').value;
        const email = document.getElementById('user-email').value;
        const password = document.getElementById('user-password').value;
        const passwordConfirm = document.getElementById('user-password-confirm').value;

        // Check if passwords match if provided
        if (password && password !== passwordConfirm) {
            showNotification('As senhas não coincidem', 'error');
            return;
        }

        // Show loading state
        const submitBtn = profileForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        // Call update profile API
        updateProfile(name, email, password)
            .then(data => {
                // Update user data
                const user = JSON.parse(localStorage.getItem('user'));
                user.name = name;
                user.email = email;
                localStorage.setItem('user', JSON.stringify(user));

                // Update UI
                loadUserData();

                // Show success message
                showNotification('Perfil atualizado com sucesso!', 'success');

                // Clear password fields
                document.getElementById('user-password').value = '';
                document.getElementById('user-password-confirm').value = '';
            })
            .catch(error => {
                console.error('Erro ao atualizar perfil:', error);
                showNotification('Erro ao atualizar perfil. Tente novamente.', 'error');
            })
            .finally(() => {
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Alterações';
            });
    });

    // API form
    const apiForm = document.getElementById('api-form');

    apiForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const fourcomApiKey = document.getElementById('4com-api-key').value;
        const fourcomApiUrl = document.getElementById('4com-api-url').value;
        const openaiApiKey = document.getElementById('openai-api-key').value;

        // Show loading state
        const submitBtn = apiForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        // Call update API settings API
        updateApiSettings(fourcomApiKey, fourcomApiUrl, openaiApiKey)
            .then(data => {
                // Show success message
                showNotification('Configurações de API atualizadas com sucesso!', 'success');
            })
            .catch(error => {
                console.error('Erro ao atualizar configurações de API:', error);
                showNotification('Erro ao atualizar configurações de API. Tente novamente.', 'error');
            })
            .finally(() => {
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Configurações';
            });
    });

    // Preferences form
    const preferencesForm = document.getElementById('preferences-form');

    preferencesForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const language = document.getElementById('language-preference').value;
        const theme = document.getElementById('theme-preference').value;
        const notifications = document.getElementById('notifications-preference').checked;
        const autoTranscribe = document.getElementById('auto-transcribe-preference').checked;

        // Show loading state
        const submitBtn = preferencesForm.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';

        // Call update preferences API
        updatePreferences(language, theme, notifications, autoTranscribe)
            .then(data => {
                // Show success message
                showNotification('Preferências atualizadas com sucesso!', 'success');

                // Apply theme if changed
                if (theme === 'dark') {
                    document.body.classList.add('dark-theme');
                } else {
                    document.body.classList.remove('dark-theme');
                }
            })
            .catch(error => {
                console.error('Erro ao atualizar preferências:', error);
                showNotification('Erro ao atualizar preferências. Tente novamente.', 'error');
            })
            .finally(() => {
                // Reset button state
                submitBtn.disabled = false;
                submitBtn.textContent = 'Salvar Preferências';
            });
    });
}

// Setup dashboard
function setupDashboard() {
    // Apply filters button
    const applyFiltersBtn = document.getElementById('apply-filters-btn');

    applyFiltersBtn.addEventListener('click', function() {
        loadDashboardData();
    });

    // Export dashboard button
    const exportDashboardBtn = document.getElementById('export-dashboard-btn');

    exportDashboardBtn.addEventListener('click', function() {
        // Get filter values
        const startDate = document.getElementById('dashboard-start-date').value;
        const endDate = document.getElementById('dashboard-end-date').value;
        const operator = document.getElementById('dashboard-operator').value;
        const sentiment = document.getElementById('dashboard-sentiment').value;

        // Build query string
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (operator) params.append('operator', operator);
        if (sentiment) params.append('sentiment', sentiment);

        // Export dashboard
        window.open(`${apiBaseUrl}/export/dashboard/csv?${params.toString()}`, '_blank');
    });

    // Initialize charts
    initializeCharts();
}

// Initialize charts
function initializeCharts() {
    // Calls chart
    const callsChartCtx = document.getElementById('calls-chart').getContext('2d');
    chartInstances.callsChart = new Chart(callsChartCtx, {
        type: 'line',
        data: {
            labels: ['12/05', '13/05', '14/05', '15/05', '16/05', '17/05', '18/05'],
            datasets: [{
                label: 'Chamadas',
                data: [12, 19, 15, 17, 22, 24, 19],
                backgroundColor: 'rgba(67, 97, 238, 0.2)',
                borderColor: 'rgba(67, 97, 238, 1)',
                borderWidth: 2,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    // Sentiment chart
    const sentimentChartCtx = document.getElementById('sentiment-chart').getContext('2d');
    chartInstances.sentimentChart = new Chart(sentimentChartCtx, {
        type: 'doughnut',
        data: {
            labels: ['Positivo', 'Neutro', 'Negativo'],
            datasets: [{
                data: [65, 25, 10],
                backgroundColor: [
                    'rgba(76, 201, 240, 0.7)',
                    'rgba(248, 150, 30, 0.7)',
                    'rgba(249, 65, 68, 0.7)'
                ],
                borderColor: [
                    'rgba(76, 201, 240, 1)',
                    'rgba(248, 150, 30, 1)',
                    'rgba(249, 65, 68, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Keywords chart
    const keywordsChartCtx = document.getElementById('keywords-chart').getContext('2d');
    chartInstances.keywordsChart = new Chart(keywordsChartCtx, {
        type: 'bar',
        data: {
            labels: ['internet', 'problema', 'solução', 'contrato', 'fatura', 'pagamento', 'cancelamento', 'técnico', 'velocidade', 'suporte'],
            datasets: [{
                label: 'Frequência',
                data: [25, 18, 15, 12, 10, 8, 7, 6, 5, 4],
                backgroundColor: 'rgba(67, 97, 238, 0.7)',
                borderColor: 'rgba(67, 97, 238, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

    // Operators chart
    const operatorsChartCtx = document.getElementById('operators-chart').getContext('2d');
    chartInstances.operatorsChart = new Chart(operatorsChartCtx, {
        type: 'bar',
        data: {
            labels: ['Operador 1', 'Operador 2', 'Operador 3'],
            datasets: [
                {
                    label: 'Chamadas',
                    data: [45, 35, 48],
                    backgroundColor: 'rgba(67, 97, 238, 0.7)',
                    borderColor: 'rgba(67, 97, 238, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Sentimento Médio',
                    data: [0.7, 0.3, 0.5],
                    backgroundColor: 'rgba(76, 201, 240, 0.7)',
                    borderColor: 'rgba(76, 201, 240, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Show login modal
function showLoginModal() {
    const loginModal = document.getElementById('login-modal');
    loginModal.classList.add('active');
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="close-notification">&times;</button>
    `;

    // Add to document
    document.body.appendChild(notification);

    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 5000);

    // Close button
    const closeBtn = notification.querySelector('.close-notification');
    closeBtn.addEventListener('click', () => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
}

// Get notification icon based on type
function getNotificationIcon(type) {
    switch (type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

// Load user data
function loadUserData() {
    const userJson = localStorage.getItem('user');
    if (userJson) {
        currentUser = JSON.parse(userJson);

        // Update user info in sidebar
        document.querySelector('.user-name').textContent = currentUser.name;
        document.querySelector('.user-role').textContent = currentUser.role ? currentUser.role.charAt(0).toUpperCase() + currentUser.role.slice(1) : 'Usuário';

        // Update profile form
        document.getElementById('user-name').value = currentUser.name;
        document.getElementById('user-email').value = currentUser.email;
    }
}

// Load recordings
async function loadRecordings() {
    try {
        const response = await fetch(`${apiBaseUrl}/upload/recordings`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar gravações');
        }

        const data = await response.json();
        updateRecordingsTable(data);
    } catch (error) {
        console.error('Erro ao carregar gravações:', error);
        showNotification('Erro ao carregar gravações', 'error');
    }
}

// Update recordings table
function updateRecordingsTable(recordings) {
    const table = document.getElementById('recordings-table');
    table.innerHTML = '';

    if (recordings && recordings.length > 0) {
        recordings.forEach(recording => {
            const row = document.createElement('tr');

            // Title
            const titleCell = document.createElement('td');
            titleCell.textContent = recording.title || `Gravação ${recording.id}`;
            row.appendChild(titleCell);

            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = formatDate(recording.created_at) + ' ' + formatTime(recording.created_at);
            row.appendChild(dateCell);

            // Type
            const typeCell = document.createElement('td');
            typeCell.textContent = recording.file_type || 'Desconhecido';
            row.appendChild(typeCell);

            // Status
            const statusCell = document.createElement('td');
            const statusBadge = document.createElement('span');
            statusBadge.className = `badge badge-${getStatusClass(recording.status)}`;
            statusBadge.textContent = getStatusText(recording.status);
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);

            // Actions
            const actionsCell = document.createElement('td');

            // View button
            const viewBtn = document.createElement('button');
            viewBtn.className = 'btn btn-icon btn-sm';
            viewBtn.title = 'Ver Transcrição';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i>';

            if (recording.status !== 'completed') {
                viewBtn.disabled = true;
            } else {
                viewBtn.addEventListener('click', () => {
                    loadTranscriptionDetails(recording.transcription_id)
                        .then(data => {
                            // Update modal with transcription details
                            updateTranscriptionModal(data);

                            // Show modal
                            document.getElementById('transcription-modal').classList.add('active');
                        })
                        .catch(error => {
                            console.error('Erro ao carregar detalhes da transcrição:', error);
                            showNotification('Erro ao carregar detalhes da transcrição', 'error');
                        });
                });
            }

            actionsCell.appendChild(viewBtn);

            // Download button
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-icon btn-sm';
            downloadBtn.title = 'Baixar';
            downloadBtn.innerHTML = '<i class="fas fa-download"></i>';
            downloadBtn.addEventListener('click', () => {
                window.open(`${apiBaseUrl}/upload/recordings/${recording.id}/download`, '_blank');
            });
            actionsCell.appendChild(downloadBtn);

            // Delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-icon btn-sm btn-danger';
            deleteBtn.title = 'Excluir';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.addEventListener('click', () => {
                if (confirm('Tem certeza que deseja excluir esta gravação?')) {
                    deleteRecording(recording.id)
                        .then(() => {
                            loadRecordings();
                            showNotification('Gravação excluída com sucesso!', 'success');
                        })
                        .catch(error => {
                            console.error('Erro ao excluir gravação:', error);
                            showNotification('Erro ao excluir gravação', 'error');
                        });
                }
            });
            actionsCell.appendChild(deleteBtn);

            row.appendChild(actionsCell);

            table.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 5;
        cell.textContent = 'Nenhuma gravação encontrada';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        table.appendChild(row);
    }
}

// Get status class based on status
function getStatusClass(status) {
    switch (status) {
        case 'completed': return 'success';
        case 'processing': return 'warning';
        case 'error': return 'danger';
        default: return 'info';
    }
}

// Get status text based on status
function getStatusText(status) {
    switch (status) {
        case 'completed': return 'Concluído';
        case 'processing': return 'Processando';
        case 'error': return 'Erro';
        default: return 'Pendente';
    }
}

// Format time (ISO to HH:MM)
function formatTime(isoDate) {
    if (!isoDate) return '';
    const date = new Date(isoDate);
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
}

// Load dashboard data
async function loadDashboardData() {
    try {
        // Get filter values
        const startDate = document.getElementById('dashboard-start-date').value;
        const endDate = document.getElementById('dashboard-end-date').value;
        const operator = document.getElementById('dashboard-operator').value;
        const sentiment = document.getElementById('dashboard-sentiment').value;

        // Build query string
        const params = new URLSearchParams();
        if (startDate) params.append('start_date', startDate);
        if (endDate) params.append('end_date', endDate);
        if (operator) params.append('operator', operator);
        if (sentiment) params.append('sentiment', sentiment);

        // Call dashboard API
        const response = await fetch(`${apiBaseUrl}/dashboard/stats?${params.toString()}`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar dados do dashboard');
        }

        const data = await response.json();
        updateDashboardStats(data);
        updateDashboardCharts(data);
        loadRecentTranscriptions();
    } catch (error) {
        console.error('Erro ao carregar dados do dashboard:', error);
        showNotification('Erro ao carregar dados do dashboard', 'error');
    }
}

function logout() {
    // Limpar localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // Chamar endpoint de logout para limpar cookies
    fetch('/api/auth/logout', {
        method: 'POST'
    })
    .finally(() => {
        // Redirecionar para login
        window.location.href = '/login';
    });
}

// Adicionar evento ao botão de logout quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', logout);
    }
});

// Update dashboard stats
function updateDashboardStats(data) {
    // Total calls
    document.querySelector('.stat-card:nth-child(1) .stat-value').textContent = data.total_calls || 0;

    // Average TMA
    document.querySelector('.stat-card:nth-child(2) .stat-value').textContent = formatDuration(data.average_tma) || '0:00';

    // Average sentiment
    const sentimentValue = data.average_sentiment || 0;
    document.querySelector('.stat-card:nth-child(3) .stat-value').textContent = sentimentValue.toFixed(2);

    const sentimentIndicator = document.querySelector('.stat-card:nth-child(3) .sentiment-indicator');
    if (sentimentValue >= 0.3) {
        sentimentIndicator.className = 'sentiment-indicator positive';
    } else if (sentimentValue <= -0.3) {
        sentimentIndicator.className = 'sentiment-indicator negative';
    } else {
        sentimentIndicator.className = 'sentiment-indicator neutral';
    }

    // Critical moments
    document.querySelector('.stat-card:nth-child(4) .stat-value').textContent = data.critical_moments || 0;
}

// Update dashboard charts
function updateDashboardCharts(data) {
    // Calls chart
    if (data.calls_by_day) {
        chartInstances.callsChart.data.labels = data.calls_by_day.map(item => item.date);
        chartInstances.callsChart.data.datasets[0].data = data.calls_by_day.map(item => item.count);
        chartInstances.callsChart.update();
    }

    // Sentiment chart
    if (data.sentiment_distribution) {
        chartInstances.sentimentChart.data.datasets[0].data = [
            data.sentiment_distribution.positive || 0,
            data.sentiment_distribution.neutral || 0,
            data.sentiment_distribution.negative || 0
        ];
        chartInstances.sentimentChart.update();
    }

    // Keywords chart
    if (data.top_keywords) {
        chartInstances.keywordsChart.data.labels = data.top_keywords.map(item => item.text);
        chartInstances.keywordsChart.data.datasets[0].data = data.top_keywords.map(item => item.count);
        chartInstances.keywordsChart.update();
    }

    // Operators chart
    if (data.operators_performance) {
        chartInstances.operatorsChart.data.labels = data.operators_performance.map(item => item.name);
        chartInstances.operatorsChart.data.datasets[0].data = data.operators_performance.map(item => item.calls);
        chartInstances.operatorsChart.data.datasets[1].data = data.operators_performance.map(item => item.sentiment);
        chartInstances.operatorsChart.update();
    }
}

// Load recent transcriptions
async function loadRecentTranscriptions() {
    try {
        const response = await fetch(`${apiBaseUrl}/dashboard/recent-transcriptions`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar transcrições recentes');
        }

        const data = await response.json();
        updateRecentTranscriptionsTable(data);
    } catch (error) {
        console.error('Erro ao carregar transcrições recentes:', error);
        showNotification('Erro ao carregar transcrições recentes', 'error');
    }
}

// Update recent transcriptions table
function updateRecentTranscriptionsTable(transcriptions) {
    const table = document.getElementById('transcriptions-table');
    table.innerHTML = '';

    if (transcriptions && transcriptions.length > 0) {
        transcriptions.forEach(transcription => {
            const row = document.createElement('tr');

            // Title
            const titleCell = document.createElement('td');
            titleCell.textContent = transcription.title || `Transcrição ${transcription.id}`;
            row.appendChild(titleCell);

            // Operator
            const operatorCell = document.createElement('td');
            operatorCell.textContent = transcription.operator || 'Não especificado';
            row.appendChild(operatorCell);

            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = formatDate(transcription.created_at);
            row.appendChild(dateCell);

            // TMA
            const tmaCell = document.createElement('td');
            tmaCell.textContent = formatDuration(transcription.duration);
            row.appendChild(tmaCell);

            // Sentiment
            const sentimentCell = document.createElement('td');
            const sentimentIndicator = document.createElement('div');
            sentimentIndicator.className = `sentiment-indicator ${getSentimentClass(transcription.sentiment_score)}`;
            sentimentCell.appendChild(sentimentIndicator);
            sentimentCell.appendChild(document.createTextNode(getSentimentText(transcription.sentiment_score)));
            row.appendChild(sentimentCell);

            // Actions
            const actionsCell = document.createElement('td');

            // View button
            const viewBtn = document.createElement('button');
            viewBtn.className = 'btn btn-icon btn-sm';
            viewBtn.title = 'Ver Detalhes';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
            viewBtn.addEventListener('click', () => {
                loadTranscriptionDetails(transcription.id)
                    .then(data => {
                        // Update modal with transcription details
                        updateTranscriptionModal(data);

                        // Show modal
                        document.getElementById('transcription-modal').classList.add('active');
                    })
                    .catch(error => {
                        console.error('Erro ao carregar detalhes da transcrição:', error);
                        showNotification('Erro ao carregar detalhes da transcrição', 'error');
                    });
            });
            actionsCell.appendChild(viewBtn);

            // Export PDF button
            const pdfBtn = document.createElement('button');
            pdfBtn.className = 'btn btn-icon btn-sm';
            pdfBtn.title = 'Exportar PDF';
            pdfBtn.innerHTML = '<i class="fas fa-file-pdf"></i>';
            pdfBtn.addEventListener('click', () => {
                window.open(`${apiBaseUrl}/export/pdf/${transcription.id}`, '_blank');
            });
            actionsCell.appendChild(pdfBtn);

            // Export CSV button
            const csvBtn = document.createElement('button');
            csvBtn.className = 'btn btn-icon btn-sm';
            csvBtn.title = 'Exportar CSV';
            csvBtn.innerHTML = '<i class="fas fa-file-csv"></i>';
            csvBtn.addEventListener('click', () => {
                window.open(`${apiBaseUrl}/export/csv/${transcription.id}`, '_blank');
            });
            actionsCell.appendChild(csvBtn);

            row.appendChild(actionsCell);

            table.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 6;
        cell.textContent = 'Nenhuma transcrição encontrada';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        table.appendChild(row);
    }
}

// Load transcriptions
async function loadTranscriptions() {
    try {
        const response = await fetch(`${apiBaseUrl}/transcription/transcriptions`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar transcrições');
        }

        const data = await response.json();
        updateTranscriptionsTable(data);
    } catch (error) {
        console.error('Erro ao carregar transcrições:', error);
        showNotification('Erro ao carregar transcrições', 'error');
    }
}

// Update transcriptions table
function updateTranscriptionsTable(transcriptions) {
    const table = document.getElementById('all-transcriptions-table');
    table.innerHTML = '';

    if (transcriptions && transcriptions.length > 0) {
        transcriptions.forEach(transcription => {
            const row = document.createElement('tr');

            // Title
            const titleCell = document.createElement('td');
            titleCell.textContent = transcription.title || `Transcrição ${transcription.id}`;
            row.appendChild(titleCell);

            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = formatDate(transcription.created_at);
            row.appendChild(dateCell);

            // Duration
            const durationCell = document.createElement('td');
            durationCell.textContent = formatDuration(transcription.duration);
            row.appendChild(durationCell);

            // Sentiment
            const sentimentCell = document.createElement('td');
            const sentimentIndicator = document.createElement('div');
            sentimentIndicator.className = `sentiment-indicator ${getSentimentClass(transcription.sentiment_score)}`;
            sentimentCell.appendChild(sentimentIndicator);
            sentimentCell.appendChild(document.createTextNode(getSentimentText(transcription.sentiment_score)));
            row.appendChild(sentimentCell);

            // Keywords
            const keywordsCell = document.createElement('td');
            const keywordsList = document.createElement('div');
            keywordsList.className = 'keywords-list';

            if (transcription.keywords && transcription.keywords.length > 0) {
                // Show top 3 keywords
                transcription.keywords.slice(0, 3).forEach(keyword => {
                    const keywordSpan = document.createElement('span');
                    keywordSpan.className = 'keyword';
                    keywordSpan.textContent = keyword.text;
                    keywordsList.appendChild(keywordSpan);
                });
            } else {
                keywordsList.textContent = 'Nenhuma palavra-chave';
            }

            keywordsCell.appendChild(keywordsList);
            row.appendChild(keywordsCell);

            // Actions
            const actionsCell = document.createElement('td');
            const viewBtn = document.createElement('button');
            viewBtn.className = 'btn btn-primary btn-sm view-transcription-btn';
            viewBtn.setAttribute('data-id', transcription.id);
            viewBtn.textContent = 'Ver Detalhes';
            viewBtn.addEventListener('click', () => {
                loadTranscriptionDetails(transcription.id)
                    .then(data => {
                        // Update modal with transcription details
                        updateTranscriptionModal(data);

                        // Show modal
                        document.getElementById('transcription-modal').classList.add('active');
                    })
                    .catch(error => {
                        console.error('Erro ao carregar detalhes da transcrição:', error);
                        showNotification('Erro ao carregar detalhes da transcrição', 'error');
                    });
            });
            actionsCell.appendChild(viewBtn);
            row.appendChild(actionsCell);

            table.appendChild(row);
        });
    } else {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 6;
        cell.textContent = 'Nenhuma transcrição encontrada';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        table.appendChild(row);
    }
}

// Load transcription details
async function loadTranscriptionDetails(transcriptionId) {
    try {
        const response = await fetch(`${apiBaseUrl}/transcription/transcriptions/${transcriptionId}`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao carregar detalhes da transcrição');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao carregar detalhes da transcrição:', error);
        throw error;
    }
}

// Delete recording
async function deleteRecording(recordingId) {
    try {
        const response = await fetch(`${apiBaseUrl}/upload/recordings/${recordingId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            }
        });

        if (!response.ok) {
            throw new Error('Erro ao excluir gravação');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao excluir gravação:', error);
        throw error;
    }
}

// API functions
async function login(email, password) {
    try {
        const response = await fetch(`${apiBaseUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (!response.ok) {
            throw new Error('Erro ao fazer login');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao fazer login:', error);
        throw error;
    }
}

async function register(name, email, password) {
    try {
        const response = await fetch(`${apiBaseUrl}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, email, password })
        });

        if (!response.ok) {
            throw new Error('Erro ao criar conta');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao criar conta:', error);
        throw error;
    }
}

async function updateProfile(name, email, password) {
    try {
        const data = { name, email };
        if (password) {
            data.password = password;
        }

        const response = await fetch(`${apiBaseUrl}/auth/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Erro ao atualizar perfil');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao atualizar perfil:', error);
        throw error;
    }
}

async function updateApiSettings(fourcomApiKey, fourcomApiUrl, openaiApiKey) {
    try {
        const response = await fetch(`${apiBaseUrl}/auth/api-settings`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            body: JSON.stringify({
                fourcom_api_key: fourcomApiKey,
                fourcom_api_url: fourcomApiUrl,
                openai_api_key: openaiApiKey
            })
        });

        if (!response.ok) {
            throw new Error('Erro ao atualizar configurações de API');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao atualizar configurações de API:', error);
        throw error;
    }
}

async function updatePreferences(language, theme, notifications, autoTranscribe) {
    try {
        const response = await fetch(`${apiBaseUrl}/auth/preferences`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')
            },
            body: JSON.stringify({
                language,
                theme,
                notifications,
                auto_transcribe: autoTranscribe
            })
        });

        if (!response.ok) {
            throw new Error('Erro ao atualizar preferências');
        }

        return await response.json();
    } catch (error) {
        console.error('Erro ao atualizar preferências:', error);
        throw error;
    }
}
