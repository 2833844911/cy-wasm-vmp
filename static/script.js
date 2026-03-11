document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.querySelector('.browse-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const fileInfo = document.getElementById('file-info');
    const filenameSpan = document.getElementById('filename');
    const removeFileBtn = document.getElementById('remove-file');

    const uploadSection = document.querySelector('.upload-section');
    const selectionSection = document.getElementById('selection-section');
    const statusSection = document.getElementById('status-section');
    const resultSection = document.getElementById('result-section');

    const functionList = document.getElementById('function-list');
    const selectAllCheckbox = document.getElementById('select-all');
    const selectedCountSpan = document.getElementById('selected-count');
    const startProtectBtn = document.getElementById('start-protect-btn');

    const statusTitle = document.getElementById('status-title');
    const statusDesc = document.getElementById('status-desc');
    const loader = document.getElementById('loader');
    const successIcon = document.getElementById('success-icon');
    const downloadLink = document.getElementById('download-link');

    let selectedFile = null;
    let currentJobId = null;

    // Drag and Drop
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

    // Browse
    // Make the whole drop zone clickable, but avoid double-triggering or triggering on buttons
    dropZone.addEventListener('click', (e) => {
        if (e.target === uploadBtn || uploadBtn.contains(e.target) ||
            e.target === removeFileBtn || removeFileBtn.contains(e.target)) {
            return;
        }
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

    // Remove File
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        fileInfo.style.display = 'none';
        uploadBtn.disabled = true;
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.name.endsWith('.wasm')) {
                if (file.size > 1024 * 1024) { // 1MB limit
                    alert('文件大小超过 1MB 限制。');
                    return;
                }
                selectedFile = file;
                filenameSpan.textContent = file.name;
                fileInfo.style.display = 'inline-flex';
                uploadBtn.disabled = false;
            } else {
                alert('请上传有效的 .wasm 文件。');
            }
        }
    }

    // Upload & Analyze
    uploadBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        // UI Transition
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 上传中...';

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error('上传失败');

            const data = await response.json();
            currentJobId = data.job_id;

            // Analyze
            await analyzeWasm(currentJobId);

        } catch (error) {
            console.error(error);
            alert('上传过程中发生错误。');
            location.reload();
        }
    });

    async function analyzeWasm(jobId) {
        try {
            const response = await fetch(`/analyze/${jobId}`);
            if (!response.ok) throw new Error('分析失败');

            const data = await response.json();
            renderFunctionList(data.functions);

            // Transition to Selection
            uploadSection.style.display = 'none';
            selectionSection.style.display = 'block';

        } catch (error) {
            console.error(error);
            alert('分析文件失败。');
            location.reload();
        }
    }

    function renderFunctionList(funcs) {
        functionList.innerHTML = '';
        funcs.forEach(func => {
            const item = document.createElement('div');
            item.className = 'function-item';

            const label = document.createElement('label');

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = func.index;
            checkbox.className = 'func-checkbox';

            const info = document.createElement('span');
            info.className = 'func-info';
            info.textContent = `#${func.index} ${func.name || '<anonymous>'}`;

            const lines = document.createElement('span');
            lines.className = 'func-lines';
            lines.textContent = `${func.lines} 行指令`;

            label.appendChild(checkbox);
            label.appendChild(info);
            label.appendChild(lines);
            item.appendChild(label);
            functionList.appendChild(item);
        });

        updateSelectedCount();

        // Event listeners for checkboxes
        const checkboxes = document.querySelectorAll('.func-checkbox');
        checkboxes.forEach(cb => cb.addEventListener('change', updateSelectedCount));
    }

    // Select All
    selectAllCheckbox.addEventListener('change', (e) => {
        const checkboxes = document.querySelectorAll('.func-checkbox');
        checkboxes.forEach(cb => cb.checked = e.target.checked);
        updateSelectedCount();
    });

    function updateSelectedCount() {
        const checkboxes = document.querySelectorAll('.func-checkbox');
        const checked = Array.from(checkboxes).filter(cb => cb.checked);
        selectedCountSpan.textContent = `已选择 ${checked.length} 个`;

        // Update Select All state
        if (checked.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checked.length === checkboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    // Start Protection
    startProtectBtn.addEventListener('click', async () => {
        const checkboxes = document.querySelectorAll('.func-checkbox');
        const selectedIndices = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => parseInt(cb.value));

        // If none selected, maybe warn? Or imply all?
        // Let's assume if none selected, we send empty list (which might mean none encrypted, or all? Logic says none)
        // If user wants all, they should select all.
        // But wait, original logic was "all except last".
        // If user selects nothing, we should probably ask them to select something.
        if (selectedIndices.length === 0) {
            if (!confirm('您未选择任何函数。是否继续（不加密任何函数）？')) {
                return;
            }
        }

        selectionSection.style.display = 'none';
        statusSection.style.display = 'block';

        try {
            const response = await fetch('/encrypt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: currentJobId,
                    selected_functions: selectedIndices
                })
            });

            if (!response.ok) throw new Error('启动保护失败');

            pollStatus(currentJobId);

        } catch (error) {
            console.error(error);
            alert('启动保护失败。');
            location.reload();
        }
    });

    async function pollStatus(jobId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/status/${jobId}`);
                const data = await response.json();

                if (data.status === 'done') {
                    clearInterval(interval);
                    showSuccess(jobId);
                } else if (data.status === 'error') {
                    clearInterval(interval);
                    alert(`处理失败: ${data.message}`);
                    location.reload();
                }
            } catch (error) {
                console.error(error);
            }
        }, 1000);
    }

    function showSuccess(jobId) {
        loader.style.display = 'none';
        successIcon.style.display = 'block';
        statusTitle.textContent = '完成！';
        statusDesc.textContent = '正在跳转到结果...';

        setTimeout(() => {
            statusSection.style.display = 'none';
            resultSection.style.display = 'block';
            downloadLink.href = `/download/${jobId}`;
        }, 1500);
    }
});
