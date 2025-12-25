self.addEventListener('push', function(event) {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {}

  const title = data.title || 'Chalkin';
  const options = {
    body: data.body || '',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-192.png',
    data: {
      url: data.url || '/friends'
    }
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url ? event.notification.data.url : '/friends';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
      for (const client of clientList) {
        if (client.url.includes(url) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});
