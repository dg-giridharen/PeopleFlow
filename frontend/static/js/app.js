// HR Assistant Frontend JavaScript

// Global variables
let socket;
let currentEmployeeId = 'EMP001'; // Default for demo
let chatOpen = false;
let currentTheme = 'light';
let dataTable = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeTheme();
    initializeSocket();
    initializeChat();
    loadDashboardData();
    initializeAnimations();
    initializeFormValidation();
    initializeDataTables();

    // Set up event listeners
    setupEventListeners();
});

// Socket.IO initialization
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        showNotification('Connected to HR Assistant', 'success');
        updateConnectionStatus(true);
    });

    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        showNotification('Disconnected from server', 'warning');
        updateConnectionStatus(false);
    });
    
    socket.on('chat_response', function(data) {
        hideTypingIndicator();
        addMessageToChat(data.message, 'bot');

        // Update user message status to delivered
        if (data.messageId) {
            updateMessageStatus(data.messageId, 'delivered');
        }
    });
    
    socket.on('leave_request_update', function(data) {
        showNotification(`Leave request ${data.status}: ${data.message}`, 
                        data.status === 'approved' ? 'success' : 'danger');
        refreshData();
    });
    
    socket.on('asset_provision_update', function(data) {
        showNotification(`Asset provisioning ${data.status}: ${data.message}`, 
                        data.status === 'success' ? 'success' : 'danger');
        refreshData();
    });
}

// Chat functionality
function initializeChat() {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
}

function toggleChat() {
    const chatWidget = document.getElementById('chatWidget');
    const chatToggle = document.getElementById('chatToggle');
    
    chatOpen = !chatOpen;
    
    if (chatOpen) {
        chatWidget.classList.remove('collapsed');
        chatToggle.style.transform = 'rotate(0deg)';
    } else {
        chatWidget.classList.add('collapsed');
        chatToggle.style.transform = 'rotate(180deg)';
    }
}

function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (message) {
        const messageId = addMessageToChat(message, 'user');
        chatInput.value = '';

        // Show typing indicator
        showTypingIndicator();

        // Send message to server
        socket.emit('chat_message', {
            message: message,
            employee_id: currentEmployeeId,
            messageId: messageId
        });

        // Update message status
        updateMessageStatus(messageId, 'sent');
    }
}

function addMessageToChat(message, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);

    messageDiv.className = `message ${sender}-message`;
    messageDiv.setAttribute('data-message-id', messageId);

    const now = new Date();
    const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    messageDiv.innerHTML = `
        <div class="message-content">
            ${sender === 'bot' ? '<i class="fas fa-robot me-2"></i>' : ''}
            ${message}
        </div>
        <div class="message-time">${timeString}</div>
        ${sender === 'user' ? '<div class="message-status" data-status="sending"><i class="fas fa-clock"></i> Sending...</div>' : ''}
    `;

    chatMessages.appendChild(messageDiv);

    // Add animation
    messageDiv.classList.add('fade-in-up');

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageId;
}

// Event listeners setup
function setupEventListeners() {
    // Employee ID selector (if exists)
    const employeeSelect = document.getElementById('employeeSelect');
    if (employeeSelect) {
        employeeSelect.addEventListener('change', function() {
            currentEmployeeId = this.value;
            refreshEmployeeData();
        });
    }
    
    // Leave request form
    const leaveForm = document.getElementById('leaveRequestForm');
    if (leaveForm) {
        leaveForm.addEventListener('submit', handleLeaveRequest);
    }
    
    // Asset provision form
    const assetForm = document.getElementById('assetProvisionForm');
    if (assetForm) {
        assetForm.addEventListener('submit', handleAssetProvision);
    }
}

// API functions
async function apiCall(endpoint, method = 'GET', data = null) {
    showLoading(true);
    
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.error || 'API request failed');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        showNotification(`Error: ${error.message}`, 'danger');
        throw error;
    } finally {
        showLoading(false);
    }
}

// Dashboard data loading
async function loadDashboardData() {
    try {
        const stats = await apiCall('/api/dashboard/stats');
        updateDashboardStats(stats);
        
        const employees = await apiCall('/api/employees');
        updateEmployeeTable(employees.employees);
        
        const assets = await apiCall('/api/assets');
        updateAssetTable(assets.assets);
        
        const leaveBalances = await apiCall('/api/leave-balances');
        updateLeaveChart(leaveBalances.leave_balances);
        
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateDashboardStats(stats) {
    // Update stat cards
    updateStatCard('totalEmployees', stats.employees.total);
    updateStatCard('activeEmployees', stats.employees.active);
    updateStatCard('totalAssets', stats.assets.total);
    updateStatCard('availableAssets', stats.assets.available);
    updateStatCard('assetUtilization', `${stats.assets.utilization_rate}%`);
    updateStatCard('avgAnnualLeave', stats.leave.average_annual_per_employee);
}

function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
        element.classList.add('pulse');
        setTimeout(() => element.classList.remove('pulse'), 1000);
    }
}

// Table updates
function updateEmployeeTable(employees) {
    const tbody = document.getElementById('employeeTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = employees.map(emp => `
        <tr>
            <td>${emp.employee_id}</td>
            <td>${emp.name}</td>
            <td>${emp.role}</td>
            <td>${emp.department}</td>
            <td><span class="badge status-${emp.status}">${emp.status}</span></td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewEmployee('${emp.employee_id}')">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn btn-sm btn-outline-success" onclick="provisionAssets('${emp.employee_id}')">
                    <i class="fas fa-laptop"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateAssetTable(assets) {
    const tbody = document.getElementById('assetTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = assets.map(asset => `
        <tr>
            <td>${asset.asset_id}</td>
            <td>${asset.asset_type}</td>
            <td>${asset.brand} ${asset.model}</td>
            <td><span class="badge status-${asset.status}">${asset.status}</span></td>
            <td>${asset.assigned_to || '-'}</td>
            <td>
                <button class="btn btn-sm btn-outline-info" onclick="viewAsset('${asset.asset_id}')">
                    <i class="fas fa-info-circle"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// Chart functions
function updateLeaveChart(leaveBalances) {
    const ctx = document.getElementById('leaveChart');
    if (!ctx) return;
    
    const leaveTypes = ['annual_leave', 'sick_leave', 'personal_leave'];
    const data = leaveTypes.map(type => 
        leaveBalances.reduce((sum, balance) => sum + (balance[type] || 0), 0)
    );
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Annual Leave', 'Sick Leave', 'Personal Leave'],
            datasets: [{
                data: data,
                backgroundColor: ['#0d6efd', '#198754', '#ffc107'],
                borderWidth: 0
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
}

// Form handlers
async function handleLeaveRequest(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        employee_id: formData.get('employee_id') || currentEmployeeId,
        start_date: formData.get('start_date'),
        end_date: formData.get('end_date'),
        leave_type: formData.get('leave_type')
    };
    
    try {
        const result = await apiCall('/api/leave-requests', 'POST', data);
        
        if (result.success) {
            showNotification('Leave request submitted successfully!', 'success');
            e.target.reset();
            refreshData();
        } else {
            showNotification(result.message, 'danger');
        }
    } catch (error) {
        showNotification('Failed to submit leave request', 'danger');
    }
}

async function handleAssetProvision(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        employee_id: formData.get('employee_id')
    };
    
    try {
        const result = await apiCall('/api/assets/provision', 'POST', data);
        
        if (result.success) {
            showNotification('Assets provisioned successfully!', 'success');
            e.target.reset();
            refreshData();
        } else {
            showNotification(result.message, 'danger');
        }
    } catch (error) {
        showNotification('Failed to provision assets', 'danger');
    }
}

// Utility functions
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.toggle('d-none', !show);
    }
}

function showNotification(message, type = 'info') {
    const toast = document.getElementById('notificationToast');
    const toastBody = document.getElementById('toastBody');
    
    if (toast && toastBody) {
        toastBody.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${getIconForType(type)} me-2 text-${type}"></i>
                ${message}
            </div>
        `;
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

function getIconForType(type) {
    const icons = {
        success: 'check-circle',
        danger: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function refreshData() {
    loadDashboardData();
    refreshEmployeeData();
}

async function refreshEmployeeData() {
    if (currentEmployeeId) {
        try {
            const employee = await apiCall(`/api/employees/${currentEmployeeId}`);
            const balance = await apiCall(`/api/employees/${currentEmployeeId}/leave-balance`);
            const assets = await apiCall(`/api/employees/${currentEmployeeId}/assets`);
            
            updateEmployeeInfo(employee, balance, assets);
        } catch (error) {
            console.error('Failed to refresh employee data:', error);
        }
    }
}

function updateEmployeeInfo(employee, balance, assets) {
    // Update employee info display
    const employeeInfo = document.getElementById('employeeInfo');
    if (employeeInfo && employee) {
        employeeInfo.innerHTML = `
            <h4>${employee.name}</h4>
            <p class="mb-1"><strong>ID:</strong> ${employee.employee_id}</p>
            <p class="mb-1"><strong>Role:</strong> ${employee.role}</p>
            <p class="mb-0"><strong>Department:</strong> ${employee.department}</p>
        `;
    }
    
    // Update leave balance display
    const leaveBalance = document.getElementById('leaveBalance');
    if (leaveBalance && balance) {
        leaveBalance.innerHTML = `
            <div class="row text-center">
                <div class="col-4">
                    <div class="h3 mb-0">${balance.annual_leave}</div>
                    <small>Annual</small>
                </div>
                <div class="col-4">
                    <div class="h3 mb-0">${balance.sick_leave}</div>
                    <small>Sick</small>
                </div>
                <div class="col-4">
                    <div class="h3 mb-0">${balance.personal_leave}</div>
                    <small>Personal</small>
                </div>
            </div>
        `;
    }
}

// Enhanced Action functions
async function viewEmployee(employeeId) {
    try {
        showLoading(true);
        const employee = await apiCall(`/api/employees/${employeeId}`);
        showDetailModal(`Employee Details - ${employee.name}`, employee, 'employee');
        currentEmployeeId = employeeId;
        await refreshEmployeeData();
    } catch (error) {
        showNotification('Failed to load employee details', 'danger');
    } finally {
        showLoading(false);
    }
}

async function provisionAssets(employeeId) {
    try {
        const result = await apiCall('/api/assets/provision', 'POST', { employee_id: employeeId });
        
        if (result.success) {
            showNotification(`Assets provisioned for ${employeeId}`, 'success');
            refreshData();
        } else {
            showNotification(result.message, 'warning');
        }
    } catch (error) {
        showNotification('Failed to provision assets', 'danger');
    }
}

async function viewAsset(assetId) {
    try {
        showLoading(true);
        const assets = await apiCall('/api/assets');
        const asset = assets.assets.find(a => a.asset_id === assetId);

        if (asset) {
            showDetailModal(`Asset Details - ${asset.brand} ${asset.model}`, asset, 'asset');
        } else {
            showNotification('Asset not found', 'danger');
        }
    } catch (error) {
        showNotification('Failed to load asset details', 'danger');
    } finally {
        showLoading(false);
    }
}

// Theme Management
function initializeTheme() {
    // Load saved theme or default to light
    const savedTheme = localStorage.getItem('hr-assistant-theme') || 'light';
    setTheme(savedTheme);
}

function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function setTheme(theme) {
    currentTheme = theme;
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('hr-assistant-theme', theme);

    // Update theme toggle icon
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.classList.add('spin');
        setTimeout(() => themeToggle.classList.remove('spin'), 500);
    }

    // Trigger theme change event
    document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
}

// Animation Management
function initializeAnimations() {
    // Add intersection observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all cards and major elements
    document.querySelectorAll('.card, .stat-card, .table').forEach(el => {
        observer.observe(el);
    });
}

function animateElement(element, animationClass = 'fade-in-up') {
    element.classList.add(animationClass);

    // Remove animation class after animation completes
    element.addEventListener('animationend', () => {
        element.classList.remove(animationClass);
    }, { once: true });
}

function showLoadingSkeleton(container) {
    const skeletonHTML = `
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-text"></div>
        <div class="skeleton skeleton-text" style="width: 80%;"></div>
        <div class="skeleton skeleton-text" style="width: 60%;"></div>
    `;

    if (container) {
        container.innerHTML = skeletonHTML;
    }
}

function hideLoadingSkeleton(container, content) {
    if (container) {
        container.innerHTML = content;
        animateElement(container);
    }
}

// Enhanced Form Validation
function initializeFormValidation() {
    // Add real-time validation to all forms
    document.querySelectorAll('form').forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            // Add validation container
            if (!input.closest('.form-group')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'form-group has-validation';
                input.parentNode.insertBefore(wrapper, input);
                wrapper.appendChild(input);

                // Add validation indicator
                const indicator = document.createElement('div');
                indicator.className = 'validation-indicator';
                wrapper.appendChild(indicator);

                // Add feedback container
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                wrapper.appendChild(feedback);
            }

            // Add event listeners
            input.addEventListener('input', () => validateField(input));
            input.addEventListener('blur', () => validateField(input));
        });

        // Add form submit validation
        form.addEventListener('submit', (e) => {
            if (!validateForm(form)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
}

function validateField(field) {
    const value = field.value.trim();
    const type = field.type;
    const required = field.hasAttribute('required');
    const wrapper = field.closest('.form-group');
    const indicator = wrapper?.querySelector('.validation-indicator');
    const feedback = wrapper?.querySelector('.invalid-feedback');

    let isValid = true;
    let message = '';

    // Required validation
    if (required && !value) {
        isValid = false;
        message = 'This field is required';
    }

    // Type-specific validation
    if (value && isValid) {
        switch (type) {
            case 'email':
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    isValid = false;
                    message = 'Please enter a valid email address';
                }
                break;

            case 'date':
                const selectedDate = new Date(value);
                const today = new Date();
                today.setHours(0, 0, 0, 0);

                if (field.name === 'start_date' || field.name === 'end_date') {
                    if (selectedDate < today) {
                        isValid = false;
                        message = 'Date cannot be in the past';
                    }
                }
                break;

            case 'text':
                if (field.name === 'employee_id') {
                    const empIdRegex = /^EMP\d{3}$/;
                    if (!empIdRegex.test(value)) {
                        isValid = false;
                        message = 'Employee ID must be in format EMP001';
                    }
                }
                break;
        }
    }

    // Custom validation rules
    if (value && isValid) {
        if (field.name === 'end_date') {
            const startDateField = field.form.querySelector('[name="start_date"]');
            if (startDateField && startDateField.value) {
                const startDate = new Date(startDateField.value);
                const endDate = new Date(value);

                if (endDate <= startDate) {
                    isValid = false;
                    message = 'End date must be after start date';
                }

                const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
                if (daysDiff > 30) {
                    isValid = false;
                    message = 'Leave period cannot exceed 30 days';
                }
            }
        }
    }

    // Update field appearance
    field.classList.remove('is-valid', 'is-invalid');
    field.classList.add(isValid ? 'is-valid' : 'is-invalid');

    // Update indicator
    if (indicator) {
        indicator.innerHTML = isValid ? '<i class="fas fa-check"></i>' : '<i class="fas fa-times"></i>';
        indicator.className = `validation-indicator show ${isValid ? 'valid' : 'invalid'}`;
    }

    // Update feedback
    if (feedback) {
        feedback.textContent = message;
        feedback.style.display = isValid ? 'none' : 'block';
    }

    return isValid;
}

function validateForm(form) {
    const fields = form.querySelectorAll('input, select, textarea');
    let isFormValid = true;

    fields.forEach(field => {
        if (!validateField(field)) {
            isFormValid = false;
        }
    });

    return isFormValid;
}

// Enhanced Data Tables
function initializeDataTables() {
    // Initialize DataTables for all tables with class 'data-table'
    document.querySelectorAll('.data-table').forEach(table => {
        if (dataTable) {
            dataTable.destroy();
        }

        dataTable = $(table).DataTable({
            responsive: true,
            pageLength: 10,
            lengthMenu: [[5, 10, 25, 50, -1], [5, 10, 25, 50, "All"]],
            order: [[0, 'asc']],
            columnDefs: [
                {
                    targets: -1, // Last column (actions)
                    orderable: false,
                    searchable: false
                }
            ],
            language: {
                search: "Search:",
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoEmpty: "No entries available",
                infoFiltered: "(filtered from _MAX_ total entries)",
                paginate: {
                    first: "First",
                    last: "Last",
                    next: "Next",
                    previous: "Previous"
                }
            },
            drawCallback: function() {
                // Re-apply animations to new rows
                $(this).find('tbody tr').each(function(index) {
                    $(this).css('animation-delay', (index * 0.1) + 's');
                    $(this).addClass('fade-in-up');
                });
            }
        });
    });
}

function refreshDataTable() {
    if (dataTable) {
        dataTable.ajax.reload(null, false); // false = don't reset paging
    }
}

// Enhanced Modal Functions
function showDetailModal(title, data, type = 'employee') {
    const modalId = 'detailModal';
    let modal = document.getElementById(modalId);

    if (!modal) {
        // Create modal if it doesn't exist
        modal = createDetailModal(modalId);
        document.body.appendChild(modal);
    }

    // Update modal content
    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('.modal-body');

    modalTitle.textContent = title;
    modalBody.innerHTML = generateDetailContent(data, type);

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    // Add animation
    modal.addEventListener('shown.bs.modal', () => {
        modal.querySelector('.modal-content').classList.add('slide-in-down');
    }, { once: true });
}

function createDetailModal(id) {
    const modal = document.createElement('div');
    modal.className = 'modal fade detail-modal';
    modal.id = id;
    modal.tabIndex = -1;

    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body"></div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;

    return modal;
}

function generateDetailContent(data, type) {
    let content = '<div class="detail-grid">';

    switch (type) {
        case 'employee':
            content += `
                <div class="detail-item">
                    <div class="detail-label">Employee ID</div>
                    <div class="detail-value">${data.employee_id || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Full Name</div>
                    <div class="detail-value">${data.name || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Email</div>
                    <div class="detail-value">${data.email || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Role</div>
                    <div class="detail-value">${data.role || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Department</div>
                    <div class="detail-value">${data.department || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Hire Date</div>
                    <div class="detail-value">${data.hire_date || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Manager</div>
                    <div class="detail-value">${data.manager_id || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">
                        <span class="badge status-${data.status}">${data.status || 'N/A'}</span>
                    </div>
                </div>
            `;
            break;

        case 'asset':
            content += `
                <div class="detail-item">
                    <div class="detail-label">Asset ID</div>
                    <div class="detail-value">${data.asset_id || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Type</div>
                    <div class="detail-value">${data.asset_type || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Brand</div>
                    <div class="detail-value">${data.brand || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Model</div>
                    <div class="detail-value">${data.model || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Specifications</div>
                    <div class="detail-value">${data.specifications || 'N/A'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">
                        <span class="badge status-${data.status}">${data.status || 'N/A'}</span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Assigned To</div>
                    <div class="detail-value">${data.assigned_to || 'Unassigned'}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Purchase Date</div>
                    <div class="detail-value">${data.purchase_date || 'N/A'}</div>
                </div>
            `;
            break;
    }

    content += '</div>';
    return content;
}

function showConfirmationModal(title, message, onConfirm, type = 'danger') {
    const modalId = 'confirmationModal';
    let modal = document.getElementById(modalId);

    if (!modal) {
        modal = createConfirmationModal(modalId);
        document.body.appendChild(modal);
    }

    const modalTitle = modal.querySelector('.modal-title');
    const modalBody = modal.querySelector('.modal-body');
    const confirmBtn = modal.querySelector('.btn-confirm');

    modalTitle.textContent = title;
    modalBody.innerHTML = `<p>${message}</p>`;
    confirmBtn.className = `btn btn-${type} btn-confirm`;

    // Remove existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    // Add new event listener
    newConfirmBtn.addEventListener('click', () => {
        onConfirm();
        bootstrap.Modal.getInstance(modal).hide();
    });

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

function createConfirmationModal(id) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = id;
    modal.tabIndex = -1;

    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title"></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body"></div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger btn-confirm">Confirm</button>
                </div>
            </div>
        </div>
    `;

    return modal;
}

// Enhanced Chat Functions
function showTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    let typingIndicator = document.getElementById('typingIndicator');

    if (!typingIndicator) {
        typingIndicator = document.createElement('div');
        typingIndicator.id = 'typingIndicator';
        typingIndicator.className = 'chat-typing-indicator';
        typingIndicator.innerHTML = `
            <i class="fas fa-robot me-2"></i>
            <span>AI Assistant is typing</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(typingIndicator);
    }

    typingIndicator.classList.add('show');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.classList.remove('show');
        setTimeout(() => {
            if (typingIndicator.parentNode) {
                typingIndicator.parentNode.removeChild(typingIndicator);
            }
        }, 300);
    }
}

function updateMessageStatus(messageId, status) {
    const message = document.querySelector(`[data-message-id="${messageId}"]`);
    if (message) {
        const statusElement = message.querySelector('.message-status');
        if (statusElement) {
            statusElement.setAttribute('data-status', status);

            let statusText = '';
            let statusIcon = '';

            switch (status) {
                case 'sending':
                    statusText = 'Sending...';
                    statusIcon = 'fas fa-clock';
                    break;
                case 'sent':
                    statusText = 'Sent';
                    statusIcon = 'fas fa-check';
                    break;
                case 'delivered':
                    statusText = 'Delivered';
                    statusIcon = 'fas fa-check-double';
                    break;
                case 'read':
                    statusText = 'Read';
                    statusIcon = 'fas fa-check-double';
                    break;
            }

            statusElement.innerHTML = `<i class="${statusIcon}"></i> ${statusText}`;
            statusElement.className = `message-status ${status}`;
        }
    }
}

function sendSuggestedMessage(message) {
    const chatInput = document.getElementById('chatInput');
    chatInput.value = message;
    sendMessage();
}

function clearChat() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-content">
                    <i class="fas fa-robot me-2"></i>
                    Chat cleared. How can I help you today?
                </div>
                <div class="message-time">Just now</div>
            </div>
        `;
    }
}

function updateConnectionStatus(connected) {
    const statusContainer = document.getElementById('chatConnectionStatus');

    if (statusContainer) {
        const indicator = connected ? 'connected' : '';
        const text = connected ? 'Connected' : 'Connecting...';

        statusContainer.innerHTML = `
            <div class="connection-indicator ${indicator}"></div>
            <span>${text}</span>
        `;
    }
}
