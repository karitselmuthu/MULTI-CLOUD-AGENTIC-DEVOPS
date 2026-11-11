// Source: https://backstage.io/docs/frontend-system/architecture/plugins/
import { createFrontendPlugin, PageBlueprint } from '@backstage/frontend-plugin-api';

const requestPage = PageBlueprint.make({
  params: {
    path: '/multicloud-delivery',
    loader: () => import('./RequestPage').then(module => <module.RequestPage />),
  },
});

export const multicloudDeliveryPlugin = createFrontendPlugin({
  pluginId: 'multicloud-delivery',
  extensions: [requestPage],
});
