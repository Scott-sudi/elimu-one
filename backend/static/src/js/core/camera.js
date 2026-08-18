/**
 * Helpers caméra / QR — HTTPS obligatoire + fallbacks desktop/mobile.
 */

export function isCameraSecureContext() {
  return typeof window !== 'undefined' && window.isSecureContext === true;
}

export function cameraBlockedMessage(err) {
  const host = window.location.host || '';
  if (!isCameraSecureContext()) {
    return (
      'Caméra indisponible sur http://institut-kalunga.net.susc3383.odns.fr/ ' +
      '(HTTP non sécurisé). Utilisez la saisie manuelle du QR ci-dessous.'
    );
  }
  const name = err?.name || '';
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return (
      'Accès caméra refusé. Sur Edge/Windows : Autorisations du site → Caméra = Autoriser, ' +
      'et Paramètres Windows → Confidentialité → Caméra activée. Sinon saisie manuelle.'
    );
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return 'Aucune caméra détectée sur cet appareil. Utilisez la saisie manuelle du QR.';
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return (
      'La caméra est déjà utilisée par une autre application (Teams, Zoom, etc.). ' +
      'Fermez-la puis réessayez, ou utilisez la saisie manuelle.'
    );
  }
  return (
    'Caméra indisponible' +
    (host ? ` sur ${host}` : '') +
    '. Vérifiez les permissions Edge/Windows, ou utilisez la saisie manuelle.'
  );
}

function isLikelyMobile() {
  return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '');
}

/**
 * Essaie plusieurs contraintes vidéo jusqu’à ce que Html5Qrcode démarre.
 * Sur PC (Edge/Chrome), `facingMode: environment` échoue souvent : on privilégie
 * la webcam via getCameras() puis des contraintes simples.
 * @param {import('html5-qrcode').Html5Qrcode} instance
 * @param {object} config
 * @param {(decoded: string) => void} onSuccess
 * @param {() => void} [onFailure]
 */
export async function startHtml5QrWithFallback(instance, config, onSuccess, onFailure = () => {}) {
  if (!isCameraSecureContext()) {
    const err = new Error('INSECURE_CONTEXT');
    err.name = 'InsecureContextError';
    throw err;
  }

  const attempts = [];
  const mobile = isLikelyMobile();

  // 1) Lister les caméras (déclenche souvent la demande de permission)
  try {
    const Html5Qrcode = instance?.constructor;
    if (Html5Qrcode?.getCameras) {
      const cameras = await Html5Qrcode.getCameras();
      if (cameras?.length) {
        for (const cam of cameras) {
          if (cam?.id) attempts.push(cam.id);
        }
      }
    }
  } catch {
    // ignore — on retombe sur les contraintes MediaTrack
  }

  // 2) Contraintes : desktop d’abord "user" / true ; mobile d’abord "environment"
  if (mobile) {
    attempts.push(
      { facingMode: 'environment' },
      { facingMode: { ideal: 'environment' } },
      { facingMode: 'user' },
    );
  } else {
    attempts.push(
      { facingMode: 'user' },
      { facingMode: { ideal: 'user' } },
      true,
      { facingMode: 'environment' },
    );
  }

  // 3) Fallback enumerateDevices (après getCameras, les deviceId sont souvent renseignés)
  try {
    if (navigator.mediaDevices?.enumerateDevices) {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cams = devices.filter((d) => d.kind === 'videoinput' && d.deviceId);
      for (const cam of cams) {
        if (!attempts.includes(cam.deviceId)) {
          attempts.push({ deviceId: { exact: cam.deviceId } });
          attempts.push(cam.deviceId);
        }
      }
    }
  } catch {
    // ignore
  }

  if (!attempts.length) {
    attempts.push({ facingMode: 'user' }, true);
  }

  let lastError = null;
  for (const cameraConfig of attempts) {
    try {
      await instance.start(cameraConfig, config, onSuccess, onFailure);
      return;
    } catch (err) {
      lastError = err;
      try {
        const state = instance.getState?.();
        // Html5QrcodeScannerState: NOT_STARTED=1, SCANNING=2, PAUSED=3 (versions varient)
        if (state === 2 || state === 3) await instance.stop();
      } catch {
        // ignore
      }
    }
  }
  throw lastError || new Error('CAMERA_START_FAILED');
}
