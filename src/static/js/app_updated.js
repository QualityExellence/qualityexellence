// Arquivo: app.js
// Funções para autenticação e integração com a 4COM

// Configuração global para requisições
const API_BASE_URL = '/api';
const TOKEN_KEY = 'transcall_token';
const USER_KEY = 'transcall_user';

// Utilitários
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function getAuthHeaders() {
    const token = getToken();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

function isAuthenticated() {
    return !!getToken();
}

function redirectToLogin() {
    window.location.href = '/login.html';
}

function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    redirectToLogin();
}

// Serviço de autenticação
const authService = {
    // Login com verificação de email
    login: async (email, password) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();

            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || 'Erro ao fazer login',
                    needsConfirmation: data.error === 'Email não confirmado'
                };
            }

            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));

            return { success: true, user: data.user };
        } catch (error) {
            console.error('Erro no login:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Registro com organização
    register: async (userData) => {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            });

            const data = await response.json();

            if (!response.ok) {
                return { success: false, error: data.error || 'Erro ao registrar' };
            }

            return { success: true, message: data.message };
        } catch (error) {
            console.error('Erro no registro:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Obter perfil do usuário atual
    getProfile: async () => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/auth/profile`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao obter perfil' };
            }

            // Atualizar dados do usuário no localStorage
            localStorage.setItem(USER_KEY, JSON.stringify(data));

            return { success: true, user: data };
        } catch (error) {
            console.error('Erro ao obter perfil:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Atualizar perfil do usuário
    updateProfile: async (profileData) => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/auth/profile`, {
                method: 'PUT',
                headers: getAuthHeaders(),
                body: JSON.stringify(profileData)
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao atualizar perfil' };
            }

            return { success: true, message: data.message };
        } catch (error) {
            console.error('Erro ao atualizar perfil:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Obter informações da organização
    getOrganization: async () => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/auth/organization`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao obter organização' };
            }

            return { success: true, organization: data };
        } catch (error) {
            console.error('Erro ao obter organização:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Convidar usuário para a organização
    inviteUser: async (email, role) => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/auth/invite`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ email, role })
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao convidar usuário' };
            }

            return { success: true, message: data.message };
        } catch (error) {
            console.error('Erro ao convidar usuário:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Listar usuários da organização
    getUsers: async () => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/auth/users`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao listar usuários' };
            }

            return { success: true, users: data };
        } catch (error) {
            console.error('Erro ao listar usuários:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    }
};

// Serviço de integração com a 4COM
const fourcomService = {
    // Verificar status da conexão com a 4COM
    checkStatus: async () => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/fourcom/status`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao verificar status da 4COM' };
            }

            return {
                success: true,
                status: data.status,
                message: data.message,
                simulation: data.simulation_mode
            };
        } catch (error) {
            console.error('Erro ao verificar status da 4COM:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Obter lista de gravações da 4COM
    getRecordings: async (filters = {}) => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            // Construir query string
            const queryParams = new URLSearchParams();

            if (filters.start_date) queryParams.append('start_date', filters.start_date);
            if (filters.end_date) queryParams.append('end_date', filters.end_date);
            if (filters.agent_id) queryParams.append('agent_id', filters.agent_id);
            if (filters.customer_id) queryParams.append('customer_id', filters.customer_id);
            if (filters.limit) queryParams.append('limit', filters.limit);

            const queryString = queryParams.toString();
            const url = `${API_BASE_URL}/fourcom/recordings${queryString ? `?${queryString}` : ''}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao obter gravações da 4COM' };
            }

            return {
                success: true,
                recordings: data.recordings,
                count: data.count,
                simulation: data.simulation
            };
        } catch (error) {
            console.error('Erro ao obter gravações da 4COM:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    },

    // Importar gravação da 4COM
    importRecording: async (recordingId) => {
        try {
            if (!isAuthenticated()) {
                return { success: false, error: 'Não autenticado' };
            }

            const response = await fetch(`${API_BASE_URL}/fourcom/import`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ recording_id: recordingId })
            });

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    logout();
                    return { success: false, error: 'Sessão expirada' };
                }
                return { success: false, error: data.error || 'Erro ao importar gravação' };
            }

            return {
                success: true,
                message: data.message,
                recordingId: data.recording_id,
                status: data.status,
                simulation: data.simulation
            };
        } catch (error) {
            console.error('Erro ao importar gravação da 4COM:', error);
            return { success: false, error: 'Erro de conexão. Tente novamente.' };
        }
    }
};

// Inicialização da aplicação
document.addEventListener('DOMContentLoaded', function() {
    // Verificar autenticação em todas as páginas exceto login
    if (window.location.pathname !== '/login.html' && !isAuthenticated()) {
        redirectToLogin();
        return;
    }

    // Configurar botão de logout
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }

    // Carregar informações do usuário no header
    const userInfo = document.getElementById('user-info');
    if (userInfo) {
        const user = JSON.parse(localStorage.getItem(USER_KEY) || '{}');
        if (user.name) {
            userInfo.textContent = user.name;
        }
    }

    // Inicializar componentes específicos da página
    initPageComponents();
});

// Inicializar componentes específicos de cada página
function initPageComponents() {
    // Página de importação da 4COM
    const fourcomImportSection = document.getElementById('fourcom-import-section');
    if (fourcomImportSection) {
        initFourcomImport();
    }

    // Página de gerenciamento de usuários
    const userManagementSection = document.getElementById('user-management-section');
    if (userManagementSection) {
        initUserManagement();
    }

    // Página de perfil
    const profileSection = document.getElementById('profile-section');
    if (profileSection) {
        initProfile();
    }
}

// Inicializar componentes da página de importação da 4COM
async function initFourcomImport() {
    // Verificar status da conexão com a 4COM
    const statusResult = await fourcomService.checkStatus();
    const statusIndicator = document.getElementById('fourcom-status-indicator');
    const statusText = document.getElementById('fourcom-status-text');

    if (statusResult.success) {
        if (statusResult.status === 'connected') {
            statusIndicator.classList.add('status-connected');
            statusText.textContent = 'Conectado';
        } else {
            statusIndicator.classList.add('status-disconnected');
            statusText.textContent = statusResult.simulation ? 'Modo de simulação' : 'Desconectado';
        }
    } else {
        statusIndicator.classList.add('status-disconnected');
        statusText.textContent = 'Erro de conexão';
    }

    // Configurar formulário de filtros
    const filterForm = document.getElementById('fourcom-filter-form');
    if (filterForm) {
        filterForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const startDate = document.getElementById('filter-start-date').value;
            const endDate = document.getElementById('filter-end-date').value;

            // Validar datas
            if (startDate && endDate && new Date(startDate) > new Date(endDate)) {
                showNotification('A data inicial não pode ser posterior à data final', 'error');
                return;
            }

            // Mostrar indicador de carregamento
            const recordingsList = document.getElementById('recordings-list');
            recordingsList.innerHTML = '<div class="loading">Carregando gravações...</div>';

            // Buscar gravações
            const filters = {
                start_date: startDate,
                end_date: endDate,
                limit: 50
            };

            const result = await fourcomService.getRecordings(filters);

            if (result.success) {
                displayRecordings(result.recordings, result.simulation);
            } else {
                recordingsList.innerHTML = `<div class="error-message">${result.error}</div>`;
            }
        });
    }

    // Carregar gravações iniciais
    const recordingsList = document.getElementById('recordings-list');
    if (recordingsList) {
        recordingsList.innerHTML = '<div class="loading">Carregando gravações...</div>';

        const result = await fourcomService.getRecordings();

        if (result.success) {
            displayRecordings(result.recordings, result.simulation);
        } else {
            recordingsList.innerHTML = `<div class="error-message">${result.error}</div>`;
        }
    }
}

// Exibir lista de gravações
function displayRecordings(recordings, isSimulation) {
    const recordingsList = document.getElementById('recordings-list');

    if (!recordings || recordings.length === 0) {
        recordingsList.innerHTML = '<div class="empty-message">Nenhuma gravação encontrada</div>';
        return;
    }

    let html = '';

    recordings.forEach(recording => {
        const date = new Date(recording.date).toLocaleDateString('pt-BR');
        const duration = formatDuration(recording.duration);

        html += `
            <div class="recording-item" data-id="${recording.id}">
                <div class="recording-info">
                    <div class="recording-title">${recording.title}</div>
                    <div class="recording-meta">
                        <span>${date}</span>
                        <span>${duration}</span>
                        <span>${recording.agent_name}</span>
                    </div>
                </div>
                <div class="recording-actions">
                    <button class="btn btn-primary import-btn" data-id="${recording.id}">Importar</button>
                </div>
            </div>
        `;
    });

    if (isSimulation) {
        html = `
            <div class="simulation-notice">
                <i class="fas fa-info-circle"></i> Modo de simulação ativado. Os dados exibidos são fictícios.
            </div>
        ` + html;
    }

    recordingsList.innerHTML = html;

    // Adicionar event listeners aos botões de importação
    const importButtons = recordingsList.querySelectorAll('.import-btn');
    importButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const recordingId = this.getAttribute('data-id');
            this.disabled = true;
            this.textContent = 'Importando...';

            const result = await fourcomService.importRecording(recordingId);

            if (result.success) {
                showNotification(result.message, 'success');
                this.textContent = 'Importado';
                this.classList.remove('btn-primary');
                this.classList.add('btn-success');
            } else {
                showNotification(result.error, 'error');
                this.textContent = 'Erro';
                this.classList.remove('btn-primary');
                this.classList.add('btn-danger');

                // Restaurar após 3 segundos
                setTimeout(() => {
                    this.textContent = 'Importar';
                    this.classList.remove('btn-danger');
                    this.classList.add('btn-primary');
                    this.disabled = false;
                }, 3000);
            }
        });
    });
}

// Formatar duração em segundos para formato MM:SS
function formatDuration(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
}

// Inicializar componentes da página de gerenciamento de usuários
async function initUserManagement() {
    // Carregar lista de usuários
    const usersList = document.getElementById('users-list');
    if (usersList) {
        usersList.innerHTML = '<div class="loading">Carregando usuários...</div>';

        const result = await authService.getUsers();

        if (result.success) {
            displayUsers(result.users);
        } else {
            usersList.innerHTML = `<div class="error-message">${result.error}</div>`;
        }
    }

    // Configurar formulário de convite
    const inviteForm = document.getElementById('invite-form');
    if (inviteForm) {
        inviteForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const email = document.getElementById('invite-email').value;
            const role = document.getElementById('invite-role').value;
            const inviteButton = document.getElementById('invite-button');

            if (!email) {
                showNotification('Email é obrigatório', 'error');
                return;
            }

            inviteButton.disabled = true;
            inviteButton.textContent = 'Enviando...';

            const result = await authService.inviteUser(email, role);

            if (result.success) {
                showNotification(result.message, 'success');
                inviteForm.reset();
            } else {
                showNotification(result.error, 'error');
            }

            inviteButton.disabled = false;
            inviteButton.textContent = 'Enviar Convite';
        });
    }
}

// Exibir lista de usuários
function displayUsers(users) {
    const usersList = document.getElementById('users-list');

    if (!users || users.length === 0) {
        usersList.innerHTML = '<div class="empty-message">Nenhum usuário encontrado</div>';
        return;
    }

    let html = '';

    users.forEach(user => {
        const roleClass = `role-${user.role}`;
        const lastLogin = user.last_login ? new Date(user.last_login).toLocaleDateString('pt-BR') : 'Nunca';

        html += `
            <div class="user-item">
                <div class="user-info">
                    <div class="user-avatar">${user.name.charAt(0).toUpperCase()}</div>
                    <div>
                        <div class="user-name">${user.name}</div>
                        <div class="user-email">${user.email}</div>
                    </div>
                </div>
                <div class="user-details">
                    <div class="user-role ${roleClass}">${translateRole(user.role)}</div>
                    <div class="user-last-login">Último login: ${lastLogin}</div>
                </div>
            </div>
        `;
    });

    usersList.innerHTML = html;
}

// Traduzir papel do usuário
function translateRole(role) {
    const roles = {
        'admin': 'Administrador',
        'manager': 'Gerente',
        'operator': 'Operador'
    };

    return roles[role] || role;
}

// Inicializar componentes da página de perfil
async function initProfile() {
    // Carregar dados do perfil
    const profileForm = document.getElementById('profile-form');
    if (profileForm) {
        const result = await authService.getProfile();

        if (result.success) {
            document.getElementById('profile-name').value = result.user.name || '';
            document.getElementById('profile-email').value = result.user.email || '';
            document.getElementById('profile-role').textContent = translateRole(result.user.role);
        } else {
            showNotification(result.error, 'error');
        }

        // Configurar formulário de atualização de perfil
        profileForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const name = document.getElementById('profile-name').value;
            const currentPassword = document.getElementById('profile-current-password').value;
            const newPassword = document.getElementById('profile-new-password').value;
            const confirmPassword = document.getElementById('profile-confirm-password').value;
            const updateButton = document.getElementById('profile-update-button');

            if (!name) {
                showNotification('Nome é obrigatório', 'error');
                return;
            }

            // Validar senhas se estiver alterando
            if (newPassword) {
                if (!currentPassword) {
                    showNotification('Senha atual é obrigatória para alterar a senha', 'error');
                    return;
                }

                if (newPassword !== confirmPassword) {
                    showNotification('As senhas não coincidem', 'error');
                    return;
                }

                // Validar força da senha
                const passwordError = validatePassword(newPassword);
                if (passwordError) {
                    showNotification(passwordError, 'error');
                    return;
                }
            }

            updateButton.disabled = true;
            updateButton.textContent = 'Atualizando...';

            const profileData = { name };
            if (newPassword) {
                profileData.current_password = currentPassword;
                profileData.new_password = newPassword;
            }

            const result = await authService.updateProfile(profileData);

            if (result.success) {
                showNotification('Perfil atualizado com sucesso', 'success');

                // Limpar campos de senha
                document.getElementById('profile-current-password').value = '';
                document.getElementById('profile-new-password').value = '';
                document.getElementById('profile-confirm-password').value = '';

                // Atualizar nome no header
                const userInfo = document.getElementById('user-info');
                if (userInfo) {
                    userInfo.textContent = name;
                }

                // Atualizar dados do usuário no localStorage
                const user = JSON.parse(localStorage.getItem(USER_KEY) || '{}');
                user.name = name;
                localStorage.setItem(USER_KEY, JSON.stringify(user));
            } else {
                showNotification(result.error, 'error');
            }

            updateButton.disabled = false;
            updateButton.textContent = 'Atualizar Perfil';
        });
    }

    // Carregar dados da organização
    const orgSection = document.getElementById('organization-section');
    if (orgSection) {
        const result = await authService.getOrganization();

        if (result.success) {
            document.getElementById('org-name').textContent = result.organization.name;
            document.getElementById('org-plan').textContent = translatePlan(result.organization.plan);

            // Mostrar formulário de edição para admins
            const user = JSON.parse(localStorage.getItem(USER_KEY) || '{}');
            if (user.role === 'admin') {
                document.getElementById('org-edit-section').classList.remove('hidden');
                document.getElementById('org-edit-name').value = result.organization.name;

                // Configurar formulário de edição
                const orgForm = document.getElementById('org-form');
                if (orgForm) {
                    orgForm.addEventListener('submit', async function(e) {
                        e.preventDefault();

                        const name = document.getElementById('org-edit-name').value;
                        const updateButton = document.getElementById('org-update-button');

                        if (!name) {
                            showNotification('Nome da organização é obrigatório', 'error');
                            return;
                        }

                        updateButton.disabled = true;
                        updateButton.textContent = 'Atualizando...';

                        const result = await authService.updateOrganization({ name });

                        if (result.success) {
                            showNotification('Organização atualizada com sucesso', 'success');
                            document.getElementById('org-name').textContent = name;
                        } else {
                            showNotification(result.error, 'error');
                        }

                        updateButton.disabled = false;
                        updateButton.textContent = 'Atualizar';
                    });
                }
            }
        } else {
            orgSection.innerHTML = `<div class="error-message">${result.error}</div>`;
        }
    }
}

// Traduzir plano da organização
function translatePlan(plan) {
    const plans = {
        'basic': 'Básico',
        'pro': 'Profissional',
        'enterprise': 'Empresarial'
    };

    return plans[plan] || plan;
}

// Validar senha
function validatePassword(password) {
    if (password.length < 8) {
        return 'A senha deve ter pelo menos 8 caracteres';
    }

    if (!/[A-Z]/.test(password)) {
        return 'A senha deve conter pelo menos uma letra maiúscula';
    }

    if (!/[a-z]/.test(password)) {
        return 'A senha deve conter pelo menos uma letra minúscula';
    }

    if (!/[0-9]/.test(password)) {
        return 'A senha deve conter pelo menos um número';
    }

    return null;
}

// Mostrar notificação
function showNotification(message, type = 'info') {
    // Verificar se o elemento de notificação já existe
    let notification = document.getElementById('notification');

    // Se não existir, criar um novo
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.className = 'notification hidden';
        document.body.appendChild(notification);
    }

    // Configurar a notificação
    notification.textContent = message;
    notification.className = `notification ${type}`;

    // Mostrar a notificação
    notification.classList.remove('hidden');

    // Esconder após 5 segundos
    setTimeout(() => {
        notification.classList.add('hidden');
    }, 5000);
}
