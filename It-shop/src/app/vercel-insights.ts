import {
  inject as angularInject,
  makeEnvironmentProviders,
  provideAppInitializer,
  type EnvironmentProviders,
} from '@angular/core';
import { ActivatedRouteSnapshot, NavigationEnd, Router } from '@angular/router';
import { inject as injectAnalytics, pageview } from '@vercel/analytics';
import { injectSpeedInsights } from '@vercel/speed-insights';
import { filter } from 'rxjs';

export function matchedRoutePattern(router: Router): string {
  let route: ActivatedRouteSnapshot | undefined = router.routerState.snapshot.root;
  while (route?.children.length) {
    route = route.children[0];
  }
  const path = route?.routeConfig?.path;
  return path ? `/${path}` : '/';
}

export function provideVercelInsights(): EnvironmentProviders {
  return makeEnvironmentProviders([
    provideAppInitializer(() => {
      const router = angularInject(Router);

      injectAnalytics({ framework: 'angular', disableAutoTrack: true });
      const speedInsights = injectSpeedInsights({ framework: 'angular' });

      let lastPattern: string | null = null;
      router.events
        .pipe(filter((event) => event instanceof NavigationEnd))
        .subscribe(() => {
          const pattern = matchedRoutePattern(router);
          if (pattern === lastPattern) {
            return;
          }
          lastPattern = pattern;
          pageview({ route: pattern });
          speedInsights?.setRoute(pattern);
        });
    }),
  ]);
}
