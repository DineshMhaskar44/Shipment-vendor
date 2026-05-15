/* App-wide JS — theme toggle, sidebar, datatables init. */

(function () {
  // Theme toggle (persisted in localStorage)
  const THEME_KEY = 'svp_theme';
  const html = document.documentElement;

  function setTheme(t) {
    html.setAttribute('data-bs-theme', t);
    localStorage.setItem(THEME_KEY, t);
  }
  const stored = localStorage.getItem(THEME_KEY);
  if (stored) setTheme(stored);

  document.addEventListener('click', e => {
    if (e.target.closest('#themeToggle')) {
      const cur = html.getAttribute('data-bs-theme') || 'light';
      setTheme(cur === 'light' ? 'dark' : 'light');
    }
    if (e.target.closest('#sidebarToggle')) {
      document.querySelector('.sidebar')?.classList.toggle('open');
    }
  });

  // Auto-init DataTables on tables with .datatable
  document.addEventListener('DOMContentLoaded', () => {
    if (window.jQuery && jQuery.fn.dataTable) {
      jQuery('.datatable').each(function () {
        if (!jQuery.fn.dataTable.isDataTable(this)) {
          jQuery(this).DataTable({
            pageLength: 25,
            order: [],
            language: { search: '_INPUT_', searchPlaceholder: 'Search…' }
          });
        }
      });
    }
  });
})();
