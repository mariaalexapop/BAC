import { PrismaClient } from "@/generated/prisma/client";
import { PrismaBetterSqlite3 } from "@prisma/adapter-better-sqlite3";
import path from "path";

const globalForPrisma = globalThis as unknown as {
  prisma: InstanceType<typeof PrismaClient> | undefined;
};

function createPrismaClient() {
  const dbUrl = process.env.DATABASE_URL || "file:../../data/questions.db";
  // Strip "file:" prefix for the adapter
  const dbPath = dbUrl.replace(/^file:/, "");
  const resolvedPath = path.resolve(/*turbopackIgnore: true*/ process.cwd(), dbPath);

  const adapter = new PrismaBetterSqlite3({ url: resolvedPath });
  return new PrismaClient({ adapter });
}

export const prisma = globalForPrisma.prisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.prisma = prisma;
}
