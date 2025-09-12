def get_frontend_html():
    """Returns the complete HTML frontend for the compliance checking application."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Healthcare Compliance Assistant</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }

            .header {
                text-align: center;
                margin-bottom: 30px;
                color: white;
            }

            .header h1 {
                font-size: 2.5rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .header p {
                font-size: 1.1rem;
                opacity: 0.9;
            }

            .main-content {
                display: grid;
                grid-template-columns: 60% 40%;
                gap: 20px;
                height: calc(100vh - 200px);
            }

            .left-panel {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
            }

            .right-panel {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
            }

            .upload-section {
                margin-bottom: 25px;
            }

            .upload-area {
                border: 3px dashed #667eea;
                border-radius: 10px;
                padding: 40px;
                text-align: center;
                background: #f8f9ff;
                transition: all 0.3s ease;
                cursor: pointer;
            }

            .upload-area:hover {
                border-color: #764ba2;
                background: #f0f2ff;
            }

            .upload-area.dragover {
                border-color: #4CAF50;
                background: #e8f5e8;
            }

            .upload-icon {
                font-size: 3rem;
                color: #667eea;
                margin-bottom: 15px;
            }

            .upload-text {
                font-size: 1.2rem;
                color: #666;
                margin-bottom: 10px;
            }

            .upload-subtext {
                color: #999;
                font-size: 0.9rem;
            }

            #fileInput {
                display: none;
            }

            .file-info {
                margin-top: 15px;
                padding: 15px;
                background: #e3f2fd;
                border-radius: 8px;
                border-left: 4px solid #2196F3;
            }

            .file-name {
                font-weight: 600;
                color: #1976D2;
            }

            .file-size {
                color: #666;
                font-size: 0.9rem;
            }

            .progress-section {
                margin: 20px 0;
                display: none;
            }

            .progress-bar {
                width: 100%;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin-bottom: 10px;
            }

            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #8BC34A);
                width: 0%;
                transition: width 0.3s ease;
            }

            .progress-text {
                text-align: center;
                color: #666;
                font-size: 0.9rem;
            }

            .document-viewer {
                flex: 1;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                background: #fafafa;
                overflow-y: auto;
                display: none;
            }

            .document-content {
                line-height: 1.6;
                font-size: 14px;
            }

            .section {
                margin-bottom: 20px;
                padding: 15px;
                border-radius: 8px;
                background: white;
                border-left: 4px solid #2196F3;
            }

            .section h3 {
                color: #1976D2;
                margin-bottom: 10px;
                font-size: 1.1rem;
            }

            .section-content {
                color: #333;
            }

            .highlight-issue {
                background: #ffebee;
                border-left: 3px solid #f44336;
                padding: 2px 4px;
                border-radius: 3px;
                position: relative;
            }

            .highlight-issue::after {
                content: attr(data-severity);
                position: absolute;
                top: -20px;
                left: 0;
                background: #f44336;
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            }

            .highlight-critical {
                background: #ffebee;
                border-left: 3px solid #d32f2f;
            }

            .highlight-major {
                background: #fff3e0;
                border-left: 3px solid #ff9800;
            }

            .highlight-minor {
                background: #f3e5f5;
                border-left: 3px solid #9c27b0;
            }

            .compliance-score {
                text-align: center;
                margin-bottom: 25px;
            }

            .score-circle {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px;
                font-size: 2rem;
                font-weight: bold;
                color: white;
                position: relative;
            }

            .score-excellent {
                background: linear-gradient(135deg, #4CAF50, #8BC34A);
            }

            .score-good {
                background: linear-gradient(135deg, #8BC34A, #CDDC39);
            }

            .score-fair {
                background: linear-gradient(135deg, #FF9800, #FFC107);
            }

            .score-poor {
                background: linear-gradient(135deg, #f44336, #e91e63);
            }

            .score-label {
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 5px;
            }

            .issues-summary {
                margin-bottom: 25px;
            }

            .issue-type {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin-bottom: 8px;
                border-radius: 8px;
                font-weight: 500;
            }

            .issue-critical {
                background: #ffebee;
                color: #d32f2f;
                border-left: 4px solid #d32f2f;
            }

            .issue-major {
                background: #fff3e0;
                color: #f57c00;
                border-left: 4px solid #ff9800;
            }

            .issue-minor {
                background: #f3e5f5;
                color: #7b1fa2;
                border-left: 4px solid #9c27b0;
            }

            .issue-count {
                background: rgba(255,255,255,0.8);
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
            }

            .issues-list {
                flex: 1;
                overflow-y: auto;
            }

            .issue-item {
                padding: 15px;
                margin-bottom: 10px;
                border-radius: 8px;
                border-left: 4px solid #ddd;
                background: #f9f9f9;
            }

            .issue-item.critical {
                border-left-color: #d32f2f;
                background: #ffebee;
            }

            .issue-item.major {
                border-left-color: #ff9800;
                background: #fff3e0;
            }

            .issue-item.minor {
                border-left-color: #9c27b0;
                background: #f3e5f5;
            }

            .issue-title {
                font-weight: 600;
                margin-bottom: 5px;
                color: #333;
            }

            .issue-description {
                font-size: 0.9rem;
                color: #666;
                margin-bottom: 8px;
            }

            .issue-location {
                font-size: 0.8rem;
                color: #999;
                font-style: italic;
            }

            .btn {
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .btn-primary {
                background: linear-gradient(135deg, #667eea, #764ba2);
                color: white;
            }

            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }

            .btn-secondary {
                background: #f5f5f5;
                color: #666;
                border: 1px solid #ddd;
            }

            .btn-secondary:hover {
                background: #e0e0e0;
            }

            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none !important;
            }

            .error-message {
                background: #ffebee;
                color: #d32f2f;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #d32f2f;
                margin: 15px 0;
                display: none;
            }

            .success-message {
                background: #e8f5e8;
                color: #2e7d32;
                padding: 15px;
                border-radius: 8px;
                border-left: 4px solid #4caf50;
                margin: 15px 0;
                display: none;
            }

            .loading-spinner {
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid #f3f3f3;
                border-top: 3px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 10px;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .hidden {
                display: none !important;
            }

            @media (max-width: 1024px) {
                .main-content {
                    grid-template-columns: 1fr;
                    height: auto;
                }
                
                .left-panel, .right-panel {
                    min-height: 400px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>�� Healthcare Compliance Assistant</h1>
                <p>AI-Powered Document Validation for FDA 21 CFR Part 11 Compliance</p>
            </div>

            <div class="main-content">
                <!-- Left Panel - Document Upload & Viewer (60%) -->
                <div class="left-panel">
                    <div class="upload-section">
                        <div class="upload-area" id="uploadArea">
                            <div class="upload-icon">📄</div>
                            <div class="upload-text">Drop your document here or click to browse</div>
                            <div class="upload-subtext">Supports PDF, DOCX, and TXT files (max 128MB)</div>
                            <input type="file" id="fileInput" accept=".pdf,.docx,.txt" />
                        </div>
                        
                        <div class="file-info" id="fileInfo" style="display: none;">
                            <div class="file-name" id="fileName"></div>
                            <div class="file-size" id="fileSize"></div>
                        </div>

                        <div class="progress-section" id="progressSection">
                            <div class="progress-bar">
                                <div class="progress-fill" id="progressFill"></div>
                            </div>
                            <div class="progress-text" id="progressText">Uploading...</div>
                        </div>

                        <div style="text-align: center; margin-top: 20px;">
                            <button class="btn btn-primary" id="validateBtn" disabled>
                                <span class="btn-text">🔍 Validate Document</span>
                            </button>
                        </div>
                    </div>

                    <div class="document-viewer" id="documentViewer">
                        <h3>📋 Document Analysis</h3>
                        <div class="document-content" id="documentContent"></div>
                    </div>

                    <div class="error-message" id="errorMessage"></div>
                    <div class="success-message" id="successMessage"></div>
                </div>

                <!-- Right Panel - Compliance Score & Issues (40%) -->
                <div class="right-panel">
                    <div class="compliance-score">
                        <div class="score-label">Compliance Score</div>
                        <div class="score-circle score-excellent" id="scoreCircle">
                            <span id="scoreValue">--</span>
                        </div>
                        <div id="scoreLabel">Upload a document to begin</div>
                    </div>

                    <div class="issues-summary" id="issuesSummary" style="display: none;">
                        <h3>📊 Issues Summary</h3>
                        <div class="issue-type issue-critical">
                            <span>🚨 Critical Issues</span>
                            <span class="issue-count" id="criticalCount">0</span>
                        </div>
                        <div class="issue-type issue-major">
                            <span>⚠️ Major Issues</span>
                            <span class="issue-count" id="majorCount">0</span>
                        </div>
                        <div class="issue-type issue-minor">
                            <span>ℹ️ Minor Issues</span>
                            <span class="issue-count" id="minorCount">0</span>
                        </div>
                    </div>

                    <div class="issues-list" id="issuesList" style="display: none;">
                        <h3>�� Detailed Issues</h3>
                        <div id="issuesContainer"></div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            class ComplianceChecker {
                constructor() {
                    this.initializeElements();
                    this.setupEventListeners();
                    this.currentFile = null;
                    this.validationResults = null;
                }

                initializeElements() {
                    this.uploadArea = document.getElementById('uploadArea');
                    this.fileInput = document.getElementById('fileInput');
                    this.fileInfo = document.getElementById('fileInfo');
                    this.fileName = document.getElementById('fileName');
                    this.fileSize = document.getElementById('fileSize');
                    this.progressSection = document.getElementById('progressSection');
                    this.progressFill = document.getElementById('progressFill');
                    this.progressText = document.getElementById('progressText');
                    this.validateBtn = document.getElementById('validateBtn');
                    this.documentViewer = document.getElementById('documentViewer');
                    this.documentContent = document.getElementById('documentContent');
                    this.errorMessage = document.getElementById('errorMessage');
                    this.successMessage = document.getElementById('successMessage');
                    this.scoreCircle = document.getElementById('scoreCircle');
                    this.scoreValue = document.getElementById('scoreValue');
                    this.scoreLabel = document.getElementById('scoreLabel');
                    this.issuesSummary = document.getElementById('issuesSummary');
                    this.criticalCount = document.getElementById('criticalCount');
                    this.majorCount = document.getElementById('majorCount');
                    this.minorCount = document.getElementById('minorCount');
                    this.issuesList = document.getElementById('issuesList');
                    this.issuesContainer = document.getElementById('issuesContainer');
                }

                setupEventListeners() {
                    // File upload events
                    this.uploadArea.addEventListener('click', () => this.fileInput.click());
                    this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
                    this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
                    this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
                    this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
                    this.validateBtn.addEventListener('click', () => this.validateDocument());
                }

                handleDragOver(e) {
                    e.preventDefault();
                    this.uploadArea.classList.add('dragover');
                }

                handleDragLeave(e) {
                    e.preventDefault();
                    this.uploadArea.classList.remove('dragover');
                }

                handleDrop(e) {
                    e.preventDefault();
                    this.uploadArea.classList.remove('dragover');
                    const files = e.dataTransfer.files;
                    if (files.length > 0) {
                        this.processFile(files[0]);
                    }
                }

                handleFileSelect(e) {
                    const file = e.target.files[0];
                    if (file) {
                        this.processFile(file);
                    }
                }

                processFile(file) {
                    // Validate file type
                    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
                    if (!allowedTypes.includes(file.type) && !file.name.match(/\\.(pdf|docx|txt)$/i)) {
                        this.showError('Please select a valid PDF, DOCX, or TXT file.');
                        return;
                    }

                    // Validate file size (128MB limit)
                    const maxSize = 128 * 1024 * 1024;
                    if (file.size > maxSize) {
                        this.showError('File size must be less than 128MB.');
                        return;
                    }

                    this.currentFile = file;
                    this.displayFileInfo(file);
                    this.validateBtn.disabled = false;
                    this.hideMessages();
                }

                displayFileInfo(file) {
                    const sizeKB = Math.round(file.size / 1024);
                    const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
                    const sizeText = sizeKB < 1024 ? `${sizeKB} KB` : `${sizeMB} MB`;
                    
                    this.fileName.textContent = file.name;
                    this.fileSize.textContent = sizeText;
                    this.fileInfo.style.display = 'block';
                }

                async validateDocument() {
                    if (!this.currentFile) return;

                    this.showProgress();
                    this.validateBtn.disabled = true;
                    this.validateBtn.innerHTML = '<span class="loading-spinner"></span>Validating...';

                    try {
                        const formData = new FormData();
                        formData.append('file', this.currentFile);

                        // First, parse the document
                        this.updateProgress(25, 'Parsing document...');
                        const parseResponse = await fetch('/parse', {
                            method: 'POST',
                            body: formData,
                            headers: { 'X-Requested-With': 'fetch' }
                        });

                        if (!parseResponse.ok) {
                            throw new Error('Failed to parse document');
                        }

                        const parseData = await parseResponse.json();
                        this.updateProgress(50, 'Analyzing content...');

                        // Then validate the document
                        this.updateProgress(75, 'Checking compliance...');
                        const validateResponse = await fetch('/validate', {
                            method: 'POST',
                            body: formData,
                            headers: { 'X-Requested-With': 'fetch' }
                        });

                        if (!validateResponse.ok) {
                            throw new Error('Failed to validate document');
                        }

                        const validateData = await validateResponse.json();
                        this.updateProgress(100, 'Complete!');

                        // Process results
                        this.validationResults = validateData;
                        this.displayResults(parseData, validateData);

                    } catch (error) {
                        this.showError('Validation failed: ' + error.message);
                        this.hideProgress();
                    } finally {
                        this.validateBtn.disabled = false;
                        this.validateBtn.innerHTML = '<span class="btn-text">🔍 Validate Document</span>';
                    }
                }

                displayResults(parseData, validateData) {
                    // Display document content with highlighting
                    this.displayDocument(parseData, validateData.findings);
                    
                    // Display compliance score
                    this.displayComplianceScore(validateData.score);
                    
                    // Display issues summary
                    this.displayIssuesSummary(validateData.findings);
                    
                    // Display detailed issues
                    this.displayDetailedIssues(validateData.findings);

                    this.hideProgress();
                    this.showSuccess('Document validation completed successfully!');
                }

                displayDocument(parseData, findings) {
                    let content = '';
                    
                    if (parseData.sections) {
                        content = parseData.sections.map(section => {
                            let sectionContent = section.body;
                            
                            // Highlight issues in this section
                            findings.forEach(finding => {
                                if (finding.section === section.heading || finding.section === `Missing: ${section.heading}`) {
                                    const severity = finding.severity.toLowerCase();
                                    sectionContent = sectionContent.replace(
                                        new RegExp(finding.message.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'), 'gi'),
                                        `<span class="highlight-issue highlight-${severity}" data-severity="${severity.toUpperCase()}" title="${finding.message}">$&</span>`
                                    );
                                }
                            });
                            
                            return `
                                <div class="section">
                                    <h3>${section.heading}</h3>
                                    <div class="section-content">${sectionContent.replace(/\\n/g, '<br>')}</div>
                                </div>
                            `;
                        }).join('');
                    } else {
                        content = `<div class="section"><div class="section-content">${parseData.text || 'No content found'}</div></div>`;
                    }
                    
                    this.documentContent.innerHTML = content;
                    this.documentViewer.style.display = 'block';
                }

                displayComplianceScore(score) {
                    this.scoreValue.textContent = score;
                    
                    let scoreClass = 'score-poor';
                    let scoreLabel = 'Needs Improvement';
                    
                    if (score >= 90) {
                        scoreClass = 'score-excellent';
                        scoreLabel = 'Excellent';
                    } else if (score >= 75) {
                        scoreClass = 'score-good';
                        scoreLabel = 'Good';
                    } else if (score >= 60) {
                        scoreClass = 'score-fair';
                        scoreLabel = 'Fair';
                    }
                    
                    this.scoreCircle.className = `score-circle ${scoreClass}`;
                    this.scoreLabel.textContent = scoreLabel;
                }

                displayIssuesSummary(findings) {
                    const critical = findings.filter(f => f.severity.toLowerCase() === 'critical').length;
                    const major = findings.filter(f => f.severity.toLowerCase() === 'major').length;
                    const minor = findings.filter(f => f.severity.toLowerCase() === 'minor').length;
                    
                    this.criticalCount.textContent = critical;
                    this.majorCount.textContent = major;
                    this.minorCount.textContent = minor;
                    
                    this.issuesSummary.style.display = 'block';
                }

                displayDetailedIssues(findings) {
                    if (findings.length === 0) {
                        this.issuesContainer.innerHTML = '<div class="issue-item" style="background: #e8f5e8; border-left-color: #4caf50;"><div class="issue-title">✅ No Issues Found</div><div class="issue-description">Your document meets all compliance requirements!</div></div>';
                    } else {
                        this.issuesContainer.innerHTML = findings.map(finding => `
                            <div class="issue-item ${finding.severity.toLowerCase()}">
                                <div class="issue-title">${this.getSeverityIcon(finding.severity)} ${finding.message}</div>
                                <div class="issue-description">${finding.citation || 'No additional details available.'}</div>
                                ${finding.location ? `<div class="issue-location">Location: ${finding.location}</div>` : ''}
                            </div>
                        `).join('');
                    }
                    
                    this.issuesList.style.display = 'block';
                }

                getSeverityIcon(severity) {
                    const icons = {
                        'critical': '🚨',
                        'major': '⚠️',
                        'minor': 'ℹ️'
                    };
                    return icons[severity.toLowerCase()] || 'ℹ️';
                }

                showProgress() {
                    this.progressSection.style.display = 'block';
                    this.updateProgress(0, 'Starting validation...');
                }

                hideProgress() {
                    setTimeout(() => {
                        this.progressSection.style.display = 'none';
                    }, 1000);
                }

                updateProgress(percent, text) {
                    this.progressFill.style.width = percent + '%';
                    this.progressText.textContent = text;
                }

                showError(message) {
                    this.errorMessage.textContent = message;
                    this.errorMessage.style.display = 'block';
                    this.successMessage.style.display = 'none';
                }

                showSuccess(message) {
                    this.successMessage.textContent = message;
                    this.successMessage.style.display = 'block';
                    this.errorMessage.style.display = 'none';
                }

                hideMessages() {
                    this.errorMessage.style.display = 'none';
                    this.successMessage.style.display = 'none';
                }
            }

            // Initialize the application
            document.addEventListener('DOMContentLoaded', () => {
                new ComplianceChecker();
            });
        </script>
    </body>
    </html>
    """