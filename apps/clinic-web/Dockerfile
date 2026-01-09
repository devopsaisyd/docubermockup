FROM node:22-slim AS deps
WORKDIR /repo
RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml /repo/
COPY packages/shared/package.json /repo/packages/shared/package.json
COPY apps/clinic-web/package.json /repo/apps/clinic-web/package.json
RUN pnpm install --frozen-lockfile

FROM node:22-slim AS build
WORKDIR /repo
RUN corepack enable
COPY --from=deps /repo/node_modules /repo/node_modules
COPY --from=deps /repo/pnpm-lock.yaml /repo/pnpm-lock.yaml
COPY --from=deps /repo/package.json /repo/package.json
COPY --from=deps /repo/pnpm-workspace.yaml /repo/pnpm-workspace.yaml

COPY packages/shared /repo/packages/shared
COPY apps/clinic-web /repo/apps/clinic-web

RUN pnpm --filter @locummap/shared build
RUN pnpm --filter clinic-web build

FROM node:22-slim AS runner
WORKDIR /repo
ENV NODE_ENV=production
RUN corepack enable
COPY --from=build /repo/package.json /repo/package.json
COPY --from=build /repo/pnpm-lock.yaml /repo/pnpm-lock.yaml
COPY --from=build /repo/pnpm-workspace.yaml /repo/pnpm-workspace.yaml
COPY --from=build /repo/node_modules /repo/node_modules
COPY --from=build /repo/apps/clinic-web/package.json /repo/apps/clinic-web/package.json
COPY --from=build /repo/packages/shared /repo/packages/shared
COPY --from=build /repo/apps/clinic-web/.next /repo/apps/clinic-web/.next
COPY --from=build /repo/apps/clinic-web/public /repo/apps/clinic-web/public
COPY --from=build /repo/apps/clinic-web/next.config.ts /repo/apps/clinic-web/next.config.ts
EXPOSE 3000
CMD ["pnpm", "--filter", "clinic-web", "start"]

