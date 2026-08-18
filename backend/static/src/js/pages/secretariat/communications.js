export function initSecretariatCommunications(root = document) {
  const page = root.querySelector('[data-page="secretariat-communications"]');
  if (!page) return;

  const studentsUrl = page.dataset.studentsUrl || '';

  page.querySelectorAll('[data-communication-audience]').forEach((form) => {
    if (form.dataset.audienceBound) return;
    form.dataset.audienceBound = '1';

    const typeField = form.querySelector('[data-audience-type]');
    const classField = form.querySelector('[data-audience-class]');
    const studentField = form.querySelector('[data-audience-student]');
    if (!typeField) return;

    const setGroupVisible = (input, show) => {
      if (!input) return;
      const group = input.closest('.form-group');
      if (group) group.hidden = !show;
      input.required = Boolean(show);
      if (!show) {
        if (input.tagName === 'SELECT') input.selectedIndex = 0;
        else input.value = '';
      }
    };

    const fillStudents = async (keepSelected = false) => {
      if (!studentField || !classField || !studentsUrl) return;
      const classId = classField.value;
      const previous = keepSelected ? studentField.value : '';
      studentField.innerHTML = '<option value="">---------</option>';
      if (!classId) return;

      try {
        const response = await fetch(`${studentsUrl}?class_id=${encodeURIComponent(classId)}`, {
          headers: { Accept: 'application/json' },
        });
        if (!response.ok) return;
        const payload = await response.json();
        (payload.students || []).forEach((student) => {
          const option = document.createElement('option');
          option.value = String(student.id);
          option.textContent = student.label;
          if (previous && previous === String(student.id)) option.selected = true;
          studentField.appendChild(option);
        });
      } catch (_error) {
        // Keep empty list on network failure.
      }
    };

    const sync = () => {
      const value = typeField.value;
      const needsClass = value === 'CLASS' || value === 'STUDENT';
      const needsStudent = value === 'STUDENT';
      setGroupVisible(classField, needsClass);
      setGroupVisible(studentField, needsStudent);
      if (needsStudent && classField?.value) {
        fillStudents(true);
      } else if (!needsStudent && studentField) {
        studentField.innerHTML = '<option value="">---------</option>';
      }
    };

    typeField.addEventListener('change', () => {
      if (studentField) studentField.innerHTML = '<option value="">---------</option>';
      sync();
    });
    classField?.addEventListener('change', () => {
      if (typeField.value === 'STUDENT') fillStudents(false);
    });

    sync();
  });
}
