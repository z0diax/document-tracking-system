/* Inline edit for Profile modal across Personal, Address, and Employment sections */
(function() {
  // Get CSRF token from meta tag or global
  const profileCsrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const SELECT_CLASS = 'form-select form-select-sm pi-input';
  const INPUT_CLASS = 'form-control form-control-sm pi-input';
  
  // These will be set from data attributes on the modal
  let CHECK_BIO_ENDPOINT = '';
  let OFFICE_VALUES = [];
  const POSITION_CHOICES = ['Job Order Worker', 'Contract of Service'];
  const STATUS_CHOICES = ['Active', 'Inactive'];

  // Reusable helpers
  function createInputControl(desc, value) {
    if (desc.type === 'select') {
      const sel = document.createElement('select');
      sel.className = SELECT_CLASS;
      const options = (desc.options || []);
      options.forEach(function(opt) {
        const o = document.createElement('option');
        o.value = opt;
        o.textContent = opt === '' ? 'Select' : opt;
        if ((value || '') === opt) o.selected = true;
        sel.appendChild(o);
      });
      return sel;
    }
    const input = document.createElement('input');
    input.type = 'text';
    input.className = INPUT_CLASS;
    input.value = (value || '');
    if (desc.placeholder) input.placeholder = desc.placeholder;
    return input;
  }

  function debounce(fn, delay) {
    let t;
    return function(...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  async function checkBio(value, excludeId) {
    if (!CHECK_BIO_ENDPOINT) return { valid: true };
    const fd = new FormData();
    fd.append('bio_number', value || '');
    if (excludeId) fd.append('exclude_id', String(excludeId));
    fd.append('csrf_token', profileCsrf);
    try {
      const res = await fetch(CHECK_BIO_ENDPOINT, {
        method: 'POST',
        headers: { 'X-CSRFToken': profileCsrf },
        body: fd,
        credentials: 'same-origin'
      });
      return await res.json();
    } catch {
      return { valid: true };
    }
  }

  // Map for Personal Information labels
  const personalFieldMap = {
    'Surname':            { key: 'surname', type: 'text' },
    'First Name':         { key: 'first_name', type: 'text' },
    'Middle Name':        { key: 'middle_name', type: 'text' },
    'Name Extension (Jr., Sr., II, etc.)': { key: 'name_extension', type: 'text' },
    'Date of Birth (mm/dd/yyyy)': { key: 'date_of_birth', type: 'text', placeholder: 'mm/dd/yyyy' },
    'Place of Birth':     { key: 'place_of_birth', type: 'text' },
    'Sex':                { key: 'sex', type: 'select', options: ['', 'Male', 'Female', 'Other'] },
    'Civil Status':       { key: 'civil_status', type: 'select', options: ['', 'Single', 'Married', 'Widowed', 'Separated', 'Other'] },
    'Height (m)':         { key: 'height_m', type: 'text', placeholder: 'e.g., 1.70' },
    'Weight (kg)':        { key: 'weight_kg', type: 'text', placeholder: 'e.g., 65' },
    'Blood Type':         { key: 'blood_type', type: 'select', options: ['', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'] },
    'GSIS ID No.':        { key: 'gsis_id_no', type: 'text' },
    'PAG-IBIG ID No.':    { key: 'pagibig_id_no', type: 'text' },
    'PhilHealth No.':     { key: 'philhealth_no', type: 'text' },
    'SSS No.':            { key: 'sss_no', type: 'text' },
    'TIN':                { key: 'tin', type: 'text' },
    'Agency Employee No.':{ key: 'agency_employee_no', type: 'text' },
    'Citizenship':        { key: 'citizenship', type: 'text' },
    'Telephone No.':      { key: 'telephone_no', type: 'text' },
    'Mobile No.':         { key: 'mobile_no', type: 'text' },
    'E-mail Address':     { key: 'email_address', type: 'text' }
  };

  // Address label -> suffix mapping
  const addressLabelToSuffix = {
    'House/Block/Lot': 'house_lot',
    'Street': 'street',
    'Subdivision/Village': 'subdivision',
    'Barangay': 'barangay',
    'City/Municipality': 'city_municipality',
    'Province': 'province',
    'ZIP Code': 'zip_code'
  };

  // Employment label map (will use OFFICE_VALUES from modal data attribute)
  const employmentFieldMap = {
    'Biometric': { key: 'bio_number', type: 'text' },
    'Office':    { key: 'office', type: 'select', options: [] }, // populated dynamically
    'Position':  { key: 'position', type: 'select', options: POSITION_CHOICES },
    'Status':    { key: 'status', type: 'select', options: STATUS_CHOICES }
  };

  function enterEdit(modal) {
    if (!modal) return;
    
    // Read config from modal data attributes
    CHECK_BIO_ENDPOINT = modal.getAttribute('data-check-bio-url') || '';
    const officesJson = modal.getAttribute('data-offices') || '[]';
    try {
      OFFICE_VALUES = JSON.parse(officesJson);
    } catch {
      OFFICE_VALUES = [];
    }
    employmentFieldMap['Office'].options = OFFICE_VALUES;

    const employeeId = modal.getAttribute('id').replace('viewEmployeeModal-', '');
    const piTab = modal.querySelector('#tab-pi-' + employeeId);
    if (!piTab) return;
    const cardBody = piTab.querySelector('.card-body');
    if (!cardBody) return;

    function attachEditor(valueEl, desc, currentText) {
      if (valueEl.querySelector('.pi-input')) return null;
      valueEl.setAttribute('data-original-text', currentText);
      valueEl.innerHTML = '';
      const input = createInputControl(desc, currentText);
      input.setAttribute('data-key', desc.key);
      valueEl.appendChild(input);
      return input;
    }

    // Personal Information grid
    const personalCols = cardBody.querySelectorAll('.row.g-3 > [class^="col-"]');
    personalCols.forEach(function(col) {
      const labelEl = col.querySelector('.text-muted.small');
      const valueEl = col.querySelector('.fw-semibold');
      if (!labelEl || !valueEl) return;
      const label = (labelEl.textContent || '').trim();
      const desc = personalFieldMap[label];
      if (!desc) return;
      const currentText = (valueEl.textContent || '').trim();
      attachEditor(valueEl, desc, currentText);
    });

    // Residential and Permanent Address sections
    const sectionHeaders = cardBody.querySelectorAll('.text-muted.small.mb-1');
    sectionHeaders.forEach(function(hdr) {
      const title = (hdr.textContent || '').trim();
      const isRes = title === 'Residential Address';
      const isPerm = title === 'Permanent Address';
      if (!isRes && !isPerm) return;
      const row = hdr.parentElement && hdr.parentElement.querySelector('.row.g-2');
      if (!row) return;
      const cols = row.querySelectorAll('[class^="col-"]');
      cols.forEach(function(col) {
        const labelEl = col.querySelector('small.text-muted');
        const valueEl = col.querySelector('.fw-semibold');
        if (!labelEl || !valueEl) return;
        const label = (labelEl.textContent || '').trim();
        const suffix = addressLabelToSuffix[label];
        if (!suffix) return;
        const key = (isRes ? 'res_' : 'perm_') + suffix;
        const currentText = (valueEl.textContent || '').trim();
        attachEditor(valueEl, { key, type: 'text' }, currentText);
      });
    });

    // Employment Details (Auto-filled)
    const empHeader = Array.from(cardBody.querySelectorAll('h6.text-uppercase.text-muted.small'))
      .find(h => (h.textContent || '').includes('Employment Details'));
    if (empHeader) {
      const empRow = empHeader.parentElement && empHeader.parentElement.querySelector('.row.g-3');
      if (empRow) {
        const cols = empRow.querySelectorAll('[class^="col-"]');
        cols.forEach(function(col) {
          const labelEl = col.querySelector('.text-muted.small');
          if (!labelEl) return;
          const lbl = (labelEl.textContent || '').trim();
          const map = employmentFieldMap[lbl];
          if (!map) return;
          let valueEl = col.querySelector('.fw-semibold');
          if (!valueEl) valueEl = labelEl.nextElementSibling || col;
          const currentText = (valueEl.textContent || '').trim();
          const input = attachEditor(valueEl, map, currentText);

          // Biometric duplicate verification inline
          if (map.key === 'bio_number' && input) {
            const excludeId = parseInt(employeeId, 10) || null;
            const runCheck = debounce(async function() {
              const val = (input.value || '').trim();
              if (!val) {
                input.classList.remove('is-invalid');
                input.removeAttribute('title');
                return;
              }
              try {
                const data = await checkBio(val, excludeId);
                if (data && data.valid) {
                  input.classList.remove('is-invalid');
                  input.removeAttribute('title');
                } else {
                  input.classList.add('is-invalid');
                  input.setAttribute('title', (data && data.message) ? data.message : 'Biometric number is already taken');
                }
              } catch {
                input.classList.remove('is-invalid');
                input.removeAttribute('title');
              }
            }, 400);
            input.addEventListener('input', () => {
              input.classList.remove('is-invalid');
              runCheck();
            });
          }
        });
      }
    }

    modal.setAttribute('data-editing', '1');
    const btn = modal.querySelector('[data-action="toggle-edit"]');
    if (btn) {
      btn.innerHTML = '<i class="fas fa-save me-1"></i> Save';
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-success');
    }
  }

  function exitEdit(modal, updatedMap) {
    if (!modal) return;
    const employeeId = modal.getAttribute('id').replace('viewEmployeeModal-', '');
    const piTab = modal.querySelector('#tab-pi-' + employeeId);
    if (!piTab) return;
    const cardBody = piTab.querySelector('.card-body');
    if (!cardBody) return;

    function restoreValue(valueEl, mapKey) {
      const input = valueEl.querySelector('.pi-input');
      let newValue = (input && 'value' in input) ? input.value : (valueEl.getAttribute('data-original-text') || '');
      if (updatedMap && mapKey && (mapKey in updatedMap)) {
        newValue = updatedMap[mapKey] || '';
      }
      valueEl.innerHTML = '';
      valueEl.textContent = newValue;
      valueEl.removeAttribute('data-original-text');
    }

    // Personal
    const personalCols = cardBody.querySelectorAll('.row.g-3 > [class^="col-"]');
    personalCols.forEach(function(col) {
      const labelEl = col.querySelector('.text-muted.small');
      const valueEl = col.querySelector('.fw-semibold');
      if (!labelEl || !valueEl) return;
      const label = (labelEl.textContent || '').trim();
      const desc = personalFieldMap[label];
      if (!desc) return;
      restoreValue(valueEl, desc.key);
    });

    // Address sections
    const sectionHeaders = cardBody.querySelectorAll('.text-muted.small.mb-1');
    sectionHeaders.forEach(function(hdr) {
      const title = (hdr.textContent || '').trim();
      const isRes = title === 'Residential Address';
      const isPerm = title === 'Permanent Address';
      if (!isRes && !isPerm) return;
      const row = hdr.parentElement && hdr.parentElement.querySelector('.row.g-2');
      if (!row) return;
      const cols = row.querySelectorAll('[class^="col-"]');
      cols.forEach(function(col) {
        const labelEl = col.querySelector('small.text-muted');
        const valueEl = col.querySelector('.fw-semibold');
        if (!labelEl || !valueEl) return;
        const label = (labelEl.textContent || '').trim();
        const suffix = addressLabelToSuffix[label];
        if (!suffix) return;
        const key = (isRes ? 'res_' : 'perm_') + suffix;
        restoreValue(valueEl, key);
      });
    });

    // Employment
    const empHeader = Array.from(cardBody.querySelectorAll('h6.text-uppercase.text-muted.small'))
      .find(h => (h.textContent || '').includes('Employment Details'));
    if (empHeader) {
      const empRow = empHeader.parentElement && empHeader.parentElement.querySelector('.row.g-3');
      if (empRow) {
        const cols = empRow.querySelectorAll('[class^="col-"]');
        cols.forEach(function(col) {
          const labelEl = col.querySelector('.text-muted.small');
          if (!labelEl) return;
          const lbl = (labelEl.textContent || '').trim();
          const map = employmentFieldMap[lbl];
          if (!map) return;
          let valueEl = col.querySelector('.fw-semibold');
          if (!valueEl) valueEl = labelEl.nextElementSibling || col;
          restoreValue(valueEl, map.key);
        });
      }
    }

    modal.removeAttribute('data-editing');
    const btn = modal.querySelector('[data-action="toggle-edit"]');
    if (btn) {
      btn.innerHTML = '<i class="fas fa-pen-to-square me-1"></i> Edit Details';
      btn.classList.remove('btn-success');
      btn.classList.add('btn-primary');
    }
  }

  async function saveEdit(modal) {
    const updateUrl = modal.getAttribute('data-update-url');
    const employeeId = modal.getAttribute('id').replace('viewEmployeeModal-', '');
    const piTab = modal.querySelector('#tab-pi-' + employeeId);
    if (!updateUrl || !piTab) return;

    // Block save if any invalid input
    const invalid = piTab.querySelector('.pi-input.is-invalid');
    if (invalid) {
      invalid.focus();
      return;
    }

    // Collect values across all sections
    const inputs = piTab.querySelectorAll('.pi-input');
    const fd = new FormData();
    fd.append('csrf_token', profileCsrf);
    inputs.forEach(function(input) {
      const key = input.getAttribute('data-key');
      if (!key) return;
      fd.append(key, (input.value || '').trim());
    });

    // Submit
    let res;
    try {
      res = await fetch(updateUrl, {
        method: 'POST',
        body: fd,
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': profileCsrf }
      });
    } catch (e) {
      exitEdit(modal, null);
      return;
    }
    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (res.ok && data && data.success) {
      // Update header display name
      try {
        const header = modal.querySelector('#viewEmployeeModalLabel-' + employeeId);
        if (header && data.employee_name) {
          header.textContent = data.employee_name;
        }
        // Update subtitle if bio/position/office changed
        const subtitle = modal.querySelector('.text-white-50');
        if (subtitle && data.updated) {
          const bio = data.updated.bio_number || modal.querySelector('.text-white-50').textContent.match(/Biometric: ([^ •]+)/)?.[1] || '';
          const pos = data.updated.position || modal.querySelector('.text-white-50').textContent.match(/• ([^•]+) •/)?.[1]?.trim() || '';
          const off = data.updated.office || modal.querySelector('.text-white-50').textContent.split('•').pop()?.trim() || '';
          subtitle.textContent = `Biometric: ${bio} • ${pos} • ${off}`;
        }
      } catch (e) {}
      exitEdit(modal, data.updated || {});
    } else {
      exitEdit(modal, null);
    }
  }

  // Event delegation for Edit/Save button
  document.addEventListener('click', function(ev) {
    const btn = ev.target.closest('[data-action="toggle-edit"]');
    if (!btn) return;
    const modal = btn.closest('.modal');
    if (!modal) return;
    const editing = modal.getAttribute('data-editing') === '1';
    if (!editing) {
      enterEdit(modal);
    } else {
      saveEdit(modal);
    }
  });

  // Expose for external use if needed
  window.EmployeeProfileEdit = { enterEdit, exitEdit, saveEdit };
})();
