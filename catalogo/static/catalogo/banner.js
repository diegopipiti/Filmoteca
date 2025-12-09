// catalogo/static/catalogo/banner.js
document.addEventListener('DOMContentLoaded', function () {
  const banner = document.querySelector('.random-banner');
  if (!banner) return;

  // FRECCE: ogni click ricarica la pagina -> la view sceglie un nuovo random_movie
  banner.querySelectorAll('.amb-banner-arrow').forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.preventDefault();
      window.location.reload();
    });
  });

  // PLAY: lascia che il browser segua l'href verso movie_play (nessun preventDefault)
  const playBtn = banner.querySelector('.amb-btn-play');
  if (playBtn) {
    playBtn.addEventListener('click', function () {
      // intentionally empty: default navigation
    });
  }
});
