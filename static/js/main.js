/**
 * AMS Zone Monitor - Main JavaScript
 */

// Global variables
let socket;
let cameras = [];
let zones = {};
let gpioConfig = {};
let zoneDrawing = false;
let zonePoints = [];
let canvasContext;
let canvasOffsetX = 0;
let canvasOffsetY = 0;
let activeTab = 'monitoring';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Set up navigation
    setupNavigation();
    
    // Connect to Socket.IO
    connectWebSocket();
    
    // Load initial configuration
    loadConfiguration();
    
    // Set up event handlers
    setupEventHandlers();
});

// Navigation setup
function setupNavigation() {
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = this.getAttribute('href').replace('#', '');
            showTab(target);
        });
    });
}

// WebSocket connection
function connectWebSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateSystemStatus('connected');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateSystemStatus('disconnected');
    });
    
    socket.on('status_update', function(data) {
        updateCameraStatus(data.cameras);
        updateZoneStatus(data.zones);
        updateGPIOStatus(data.gpio);
    });
}

// Load initial configuration
function loadConfiguration() {
    // Load config via API
    fetch('/api/config')
        .then(response => response.json())
        .then(config => {
            // Store the configuration
            if (config.cameras) cameras = config.cameras;
            if (config.zones) zones = config.zones;
            if (config.gpio) gpioConfig = config.gpio;
            
            // Update UI with loaded config
            updateCameraList();
            updateZoneList();
            updateGPIOSettings();
        })
        .catch(error => {
            console.error('Error loading configuration:', error);
            showToast('Error loading configuration', 'danger');
        });
}

// Event handlers setup
function setupEventHandlers() {
    // Camera modal
    document.getElementById('add-camera-btn').addEventListener('click', openAddCameraModal);
    document.getElementById('save-camera-btn').addEventListener('click', saveCamera);
    
    // Zone modal
    document.getElementById('add-zone-btn').addEventListener('click', openAddZoneModal);
    document.getElementById('save-zone-btn').addEventListener('click', saveZone);
    document.getElementById('draw-zone-btn').addEventListener('click', startZoneDrawing);
    document.getElementById('clear-zone-btn').addEventListener('click', clearZoneDrawing);
    document.getElementById('zone-camera').addEventListener('change', loadCameraImageForZone);
    
    // GPIO settings form
    document.getElementById('gpio-settings-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveGPIOSettings();
    });
    
    // Zone canvas setup
    const canvas = document.getElementById('zone-canvas');
    canvasContext = canvas.getContext('2d');
    
    canvas.addEventListener('click', function(e) {
        if (!zoneDrawing) return;
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        addZonePoint(x, y);
    });
}

// Show active tab
function showTab(tabName) {
    // Hide all content sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.remove('d-none');
    
    // Update active nav link
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === '#' + tabName) {
            link.classList.add('active');
        }
    });
    
    activeTab = tabName;
    
    // If switching to monitoring tab, refresh the camera feeds
    if (tabName === 'monitoring') {
        updateCameraFeeds();
    }
}

// Update system status indicator
function updateSystemStatus(status) {
    const indicator = document.getElementById('status-indicator');
    
    if (status === 'connected') {
        indicator.textContent = 'System Active';
        indicator.className = 'badge bg-success me-2';
    } else {
        indicator.textContent = 'System Disconnected';
        indicator.className = 'badge bg-danger me-2';
    }
}

// Update GPIO status indicator
function updateGPIOStatus(gpioStatus) {
    const indicator = document.getElementById('gpio-status');
    
    if (gpioStatus.active) {
        indicator.textContent = `GPIO: Active (Pin ${gpioStatus.pin})`;
        indicator.className = 'badge bg-danger';
    } else {
        indicator.textContent = `GPIO: Inactive (Pin ${gpioStatus.pin})`;
        indicator.className = 'badge bg-secondary';
    }
}

// Update camera status
function updateCameraStatus(cameraStatus) {
    // Update connection status indicators for cameras
    for (const cameraId in cameraStatus) {
        const status = cameraStatus[cameraId];
        const statusElem = document.getElementById(`camera-status-${cameraId}`);
        
        if (statusElem) {
            if (status.connected) {
                statusElem.innerHTML = `<span class="indicator indicator-active"></span> Connected`;
            } else {
                statusElem.innerHTML = `<span class="indicator indicator-inactive"></span> Disconnected`;
            }
        }
    }
    
    // If on monitoring tab, update camera feeds
    if (activeTab === 'monitoring') {
        // Request updated frames for each camera
        updateCameraFeeds();
    }
}

// Update zone status
function updateZoneStatus(zoneStatus) {
    // Update zone active status indicators
    for (const zoneId in zoneStatus) {
        const status = zoneStatus[zoneId];
        const zoneElem = document.getElementById(`zone-${zoneId}`);
        
        if (zoneElem) {
            if (status.has_person) {
                zoneElem.classList.add('zone-active');
                zoneElem.classList.remove('zone-inactive');
            } else {
                zoneElem.classList.add('zone-inactive');
                zoneElem.classList.remove('zone-active');
            }
        }
    }
}

// Camera management functions
function updateCameraList() {
    const cameraList = document.getElementById('camera-list');
    
    if (cameras.length === 0) {
        cameraList.innerHTML = `
            <div class="col-12 text-center p-5">
                <p>No cameras configured.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    cameras.forEach(camera => {
        html += `
            <div class="col-md-4 mb-4">
                <div class="card config-card">
                    <div class="card-body">
                        <h5 class="card-title">${camera.name}</h5>
                        <p class="card-text text-truncate small">${camera.rtsp_url}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div id="camera-status-${camera.id}">
                                <span class="indicator indicator-warning"></span> Unknown
                            </div>
                            <div class="config-actions">
                                <button class="btn btn-sm btn-primary me-1" onclick="editCamera('${camera.id}')">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteCamera('${camera.id}')">Delete</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    cameraList.innerHTML = html;
    
    // Also update the camera dropdown in zone modal
    updateCameraDropdown();
    
    // Update camera feeds if we're on the monitoring tab
    if (activeTab === 'monitoring') {
        updateCameraFeeds();
    }
}

function updateCameraFeeds() {
    const cameraFeeds = document.getElementById('camera-feeds');
    
    if (cameras.length === 0) {
        cameraFeeds.innerHTML = `
            <div class="col-12 text-center p-5">
                <p>No cameras configured. Go to the Cameras tab to add a camera.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    cameras.forEach(camera => {
        // Find zones for this camera
        const cameraZones = [];
        for (const zoneId in zones) {
            if (zones[zoneId].camera_id === camera.id) {
                cameraZones.push({
                    id: zoneId,
                    name: zones[zoneId].name
                });
            }
        }
        
        html += `
            <div class="col-md-6 mb-4">
                <div class="camera-feed" id="zone-${camera.id}">
                    <div class="camera-feed-header">
                        <div>${camera.name}</div>
                        <div id="camera-status-${camera.id}">
                            <span class="indicator indicator-warning"></span> Unknown
                        </div>
                    </div>
                    <img src="/api/cameras/${camera.id}/stream" class="camera-feed-img" alt="${camera.name}" onerror="this.src='/static/img/no-signal.jpg'">
                    <div class="camera-status">
                        ${cameraZones.length > 0 ? 
                            cameraZones.map(zone => `<span class="badge bg-primary me-1">${zone.name}</span>`).join('') : 
                            '<span class="badge bg-secondary">No zones defined</span>'}
                    </div>
                </div>
            </div>
        `;
    });
    
    cameraFeeds.innerHTML = html;
}

function openAddCameraModal() {
    // Reset the form
    document.getElementById('camera-form').reset();
    document.getElementById('camera-id').value = '';
    document.getElementById('camera-modal-title').textContent = 'Add Camera';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('camera-modal'));
    modal.show();
}

function editCamera(cameraId) {
    // Find the camera in the array
    const camera = cameras.find(c => c.id === cameraId);
    if (!camera) return;
    
    // Fill the form with camera data
    document.getElementById('camera-id').value = camera.id;
    document.getElementById('camera-name').value = camera.name;
    document.getElementById('rtsp-url').value = camera.rtsp_url;
    document.getElementById('camera-fps').value = camera.fps || 10;
    document.getElementById('camera-modal-title').textContent = 'Edit Camera';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('camera-modal'));
    modal.show();
}

function saveCamera() {
    // Get form values
    const cameraId = document.getElementById('camera-id').value;
    const name = document.getElementById('camera-name').value;
    const rtspUrl = document.getElementById('rtsp-url').value;
    const fps = parseInt(document.getElementById('camera-fps').value) || 10;
    
    if (!name || !rtspUrl) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    // Create camera object
    const camera = {
        id: cameraId || 'camera_' + Date.now(),
        name,
        rtsp_url: rtspUrl,
        fps
    };
    
    // Update existing or add new camera
    const existingIndex = cameras.findIndex(c => c.id === camera.id);
    if (existingIndex >= 0) {
        cameras[existingIndex] = camera;
    } else {
        cameras.push(camera);
    }
    
    // Save configuration
    saveConfiguration();
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('camera-modal'));
    modal.hide();
}

function deleteCamera(cameraId) {
    if (!confirm('Are you sure you want to delete this camera? Any zones associated with it will also be removed.')) {
        return;
    }
    
    // Remove the camera from the array
    cameras = cameras.filter(c => c.id !== cameraId);
    
    // Remove any zones associated with this camera
    for (const zoneId in zones) {
        if (zones[zoneId].camera_id === cameraId) {
            delete zones[zoneId];
        }
    }
    
    // Save configuration
    saveConfiguration();
}

// Zone management functions
function updateZoneList() {
    const zoneList = document.getElementById('zone-list');
    
    if (Object.keys(zones).length === 0) {
        zoneList.innerHTML = `
            <div class="col-12 text-center p-5">
                <p>No zones configured.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    for (const zoneId in zones) {
        const zone = zones[zoneId];
        const camera = cameras.find(c => c.id === zone.camera_id);
        const cameraName = camera ? camera.name : 'Unknown Camera';
        
        html += `
            <div class="col-md-4 mb-4">
                <div class="card config-card" id="zone-${zoneId}">
                    <div class="card-body">
                        <h5 class="card-title">${zone.name}</h5>
                        <p class="card-text small">Camera: ${cameraName}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="small text-muted">${zone.coordinates ? zone.coordinates.length + ' points' : 'No area defined'}</div>
                            <div class="config-actions">
                                <button class="btn btn-sm btn-primary me-1" onclick="editZone('${zoneId}')">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="deleteZone('${zoneId}')">Delete</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    zoneList.innerHTML = html;
}

function updateCameraDropdown() {
    const dropdown = document.getElementById('zone-camera');
    
    // Clear existing options except the first one
    while (dropdown.options.length > 1) {
        dropdown.options.remove(1);
    }
    
    // Add an option for each camera
    cameras.forEach(camera => {
        const option = document.createElement('option');
        option.value = camera.id;
        option.textContent = camera.name;
        dropdown.appendChild(option);
    });
}

function openAddZoneModal() {
    // Check if we have any cameras
    if (cameras.length === 0) {
        showToast('Please add a camera first', 'warning');
        return;
    }
    
    // Reset the form
    document.getElementById('zone-form').reset();
    document.getElementById('zone-id').value = '';
    document.getElementById('zone-modal-title').textContent = 'Add Zone';
    
    // Clear the canvas
    clearZoneDrawing();
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('zone-modal'));
    modal.show();
}

function editZone(zoneId) {
    // Find the zone
    const zone = zones[zoneId];
    if (!zone) return;
    
    // Fill the form with zone data
    document.getElementById('zone-id').value = zoneId;
    document.getElementById('zone-name').value = zone.name;
    document.getElementById('zone-camera').value = zone.camera_id;
    document.getElementById('zone-modal-title').textContent = 'Edit Zone';
    
    // Clear the canvas
    clearZoneDrawing();
    
    // Load camera image and existing coordinates
    loadCameraImageForZone();
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('zone-modal'));
    modal.show();
}

function loadCameraImageForZone() {
    const cameraId = document.getElementById('zone-camera').value;
    if (!cameraId) return;
    
    const zoneId = document.getElementById('zone-id').value;
    const imageElement = document.getElementById('zone-camera-image');
    const canvas = document.getElementById('zone-canvas');
    
    // Load snapshot from camera
    imageElement.src = `/api/cameras/${cameraId}/snapshot?t=${Date.now()}`;
    imageElement.onerror = function() {
        imageElement.src = '/static/img/no-signal.jpg';
    };
    
    // When image loads, resize canvas and load existing coordinates if editing
    imageElement.onload = function() {
        canvas.width = imageElement.width;
        canvas.height = imageElement.height;
        
        // If editing an existing zone, load the coordinates
        if (zoneId && zones[zoneId] && zones[zoneId].coordinates) {
            zonePoints = [...zones[zoneId].coordinates];
            drawZoneOnCanvas();
        }
    };
}

function startZoneDrawing() {
    const cameraId = document.getElementById('zone-camera').value;
    if (!cameraId) {
        showToast('Please select a camera first', 'warning');
        return;
    }
    
    zoneDrawing = true;
    document.getElementById('draw-zone-btn').classList.add('active');
}

function addZonePoint(x, y) {
    zonePoints.push([x, y]);
    drawZoneOnCanvas();
}

function drawZoneOnCanvas() {
    const canvas = document.getElementById('zone-canvas');
    canvasContext.clearRect(0, 0, canvas.width, canvas.height);
    
    if (zonePoints.length === 0) return;
    
    // Draw the polygon
    canvasContext.beginPath();
    canvasContext.moveTo(zonePoints[0][0], zonePoints[0][1]);
    
    for (let i = 1; i < zonePoints.length; i++) {
        canvasContext.lineTo(zonePoints[i][0], zonePoints[i][1]);
    }
    
    // Close the path if we have at least 3 points
    if (zonePoints.length >= 3) {
        canvasContext.closePath();
    }
    
    canvasContext.strokeStyle = '#FF0000';
    canvasContext.lineWidth = 2;
    canvasContext.stroke();
    
    // Fill with semi-transparent red
    canvasContext.fillStyle = 'rgba(255, 0, 0, 0.2)';
    canvasContext.fill();
    
    // Draw points
    zonePoints.forEach((point, index) => {
        canvasContext.beginPath();
        canvasContext.arc(point[0], point[1], 5, 0, Math.PI * 2);
        canvasContext.fillStyle = index === 0 ? '#00FF00' : '#FF0000';
        canvasContext.fill();
    });
}

function clearZoneDrawing() {
    zonePoints = [];
    zoneDrawing = false;
    document.getElementById('draw-zone-btn').classList.remove('active');
    
    const canvas = document.getElementById('zone-canvas');
    canvasContext.clearRect(0, 0, canvas.width, canvas.height);
}

function saveZone() {
    // Get form values
    const zoneId = document.getElementById('zone-id').value;
    const name = document.getElementById('zone-name').value;
    const cameraId = document.getElementById('zone-camera').value;
    
    if (!name || !cameraId) {
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    if (zonePoints.length < 3) {
        showToast('Please draw a zone with at least 3 points', 'warning');
        return;
    }
    
    // Create zone object
    const zone = {
        name,
        camera_id: cameraId,
        coordinates: zonePoints
    };
    
    // Add or update zone
    const id = zoneId || 'zone_' + Date.now();
    zones[id] = zone;
    
    // Save configuration
    saveConfiguration();
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('zone-modal'));
    modal.hide();
}

function deleteZone(zoneId) {
    if (!confirm('Are you sure you want to delete this zone?')) {
        return;
    }
    
    // Remove the zone
    delete zones[zoneId];
    
    // Save configuration
    saveConfiguration();
}

// GPIO settings functions
function updateGPIOSettings() {
    document.getElementById('output-pin').value = gpioConfig.output_pin || 17;
    document.getElementById('active-high').checked = gpioConfig.active_high !== false;
    document.getElementById('activation-delay').value = gpioConfig.activation_delay || 0.5;
}

function saveGPIOSettings() {
    // Get form values
    const outputPin = parseInt(document.getElementById('output-pin').value);
    const activeHigh = document.getElementById('active-high').checked;
    const activationDelay = parseFloat(document.getElementById('activation-delay').value);
    
    if (isNaN(outputPin) || outputPin < 1 || outputPin > 40) {
        showToast('Please enter a valid GPIO pin (1-40)', 'warning');
        return;
    }
    
    if (isNaN(activationDelay) || activationDelay < 0) {
        showToast('Please enter a valid activation delay', 'warning');
        return;
    }
    
    // Update GPIO config
    gpioConfig.output_pin = outputPin;
    gpioConfig.active_high = activeHigh;
    gpioConfig.activation_delay = activationDelay;
    
    // Save configuration
    saveConfiguration();
    
    showToast('GPIO settings saved', 'success');
}

// Configuration save function
function saveConfiguration() {
    const config = {
        cameras,
        zones,
        gpio: gpioConfig
    };
    
    fetch('/api/config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Update UI
            updateCameraList();
            updateZoneList();
            updateGPIOSettings();
            showToast('Configuration saved', 'success');
        } else {
            showToast('Error saving configuration', 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving configuration:', error);
        showToast('Error saving configuration', 'danger');
    });
}

// Utility functions
function showToast(message, type = 'info') {
    // Create toast element if not exists
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    const id = 'toast-' + Date.now();
    const html = `
        <div id="${id}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', html);
    
    const toastElement = document.getElementById(id);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Remove after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}
