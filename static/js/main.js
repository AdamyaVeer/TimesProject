document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');
    const uploadProgress = document.getElementById('upload-progress');
    const progressBar = uploadProgress.querySelector('div');
    const startDetection = document.getElementById('start-detection');
    const threshold = document.getElementById('threshold');
    const thresholdValue = document.getElementById('threshold-value');
    const sampleRate = document.getElementById('sample-rate');
    const resultsList = document.getElementById('results-list');

    let uploadedFiles = new Set();

    function showNotification(message, isError = false) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg ${
            isError ? 'bg-red-500' : 'bg-green-500'
        } text-white z-50 max-w-md`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
    });

    // Threshold slider
    threshold.addEventListener('input', () => {
        thresholdValue.textContent = `${threshold.value}%`;
    });

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            if (file.type.startsWith('video/')) {
                if (!uploadedFiles.has(file.name)) {
                    uploadFile(file);
                    uploadedFiles.add(file.name);
                } else {
                    showNotification(`${file.name} has already been uploaded`, true);
                }
            } else {
                showNotification(`${file.name} is not a video file`, true);
            }
        });
    }

    function uploadFile(file) {
        const formData = new FormData();
        formData.append('video', file);

        // Create file item UI
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="flex-grow">
                <div class="font-medium">${file.name}</div>
                <div class="text-sm text-gray-500">${formatFileSize(file.size)}</div>
            </div>
            <button class="remove-file text-red-500 hover:text-red-700 ml-2">×</button>
        `;
        fileList.appendChild(fileItem);

        // Show progress
        uploadProgress.classList.remove('hidden');
        progressBar.style.width = '0%';

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            progressBar.style.width = '100%';
            setTimeout(() => {
                uploadProgress.classList.add('hidden');
            }, 1000);
            showNotification(`${file.name} uploaded successfully`);
        })
        .catch(error => {
            showNotification(`Upload failed: ${error.message}`, true);
            fileItem.remove();
            uploadedFiles.delete(file.name);
        });

        // Handle remove button
        fileItem.querySelector('.remove-file').addEventListener('click', () => {
            fileItem.remove();
            uploadedFiles.delete(file.name);
        });
    }

    // Start detection
    startDetection.addEventListener('click', () => {
        if (fileList.children.length === 0) {
            showNotification('Please upload some videos first', true);
            return;
        }

        const formData = new FormData();
        formData.append('threshold', threshold.value / 100);
        formData.append('sample_rate', sampleRate.value);

        startDetection.disabled = true;
        startDetection.textContent = 'Processing...';
        showNotification('Starting duplicate detection...');

        fetch('/detect', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            showNotification(`Analysis complete! Processed ${data.files_processed} files: ${data.processed_files.join(', ')}`);
            updateResults();
        })
        .catch(error => {
            showNotification(`Detection failed: ${error.message}`, true);
        })
        .finally(() => {
            startDetection.disabled = false;
            startDetection.textContent = 'Start Detection';
        });
    });

    function updateResults() {
        resultsList.innerHTML = '<div class="text-center text-gray-600 py-4">Loading results...</div>';
        
        fetch('/results')
        .then(response => response.json())
        .then(results => {
            resultsList.innerHTML = '';
            if (results.error) {
                throw new Error(results.error);
            }
            if (results.length === 0) {
                resultsList.innerHTML = '<div class="text-center text-gray-600 py-4">No duplicates found</div>';
                return;
            }
            results.forEach(result => {
                const resultItem = document.createElement('div');
                resultItem.className = 'result-item';
                resultItem.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div>
                            <h3 class="font-semibold">${result.duplicate}</h3>
                            <p class="metadata">Original: ${result.original}</p>
                            <p class="metadata">Archived: ${result.archived_date}</p>
                        </div>
                        <a href="/download/${encodeURIComponent(result.duplicate)}" 
                           class="download-button">
                            Download
                        </a>
                    </div>
                `;
                resultsList.appendChild(resultItem);
            });
        })
        .catch(error => {
            resultsList.innerHTML = `
                <div class="text-center text-red-600 py-4">
                    Error loading results: ${error.message}
                </div>
            `;
        });
    }

    // Initial results load
    updateResults();
}); 