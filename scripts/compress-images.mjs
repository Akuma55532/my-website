import { readdir, rename, stat, unlink } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const root = path.resolve('static');
const lossy = process.argv.includes('--lossy');
const extensions = new Set(lossy ? ['.jpg', '.jpeg', '.png', '.webp'] : ['.png']);

async function* images(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const file = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      yield* images(file);
    } else if (extensions.has(path.extname(entry.name).toLowerCase())) {
      yield file;
    }
  }
}

async function compress(file) {
  const ext = path.extname(file).toLowerCase();
  const before = (await stat(file)).size;
  const temp = `${file}.${process.pid}.tmp${ext}`;
  let image = sharp(file);

  if (ext === '.png') {
    image = image.png({ compressionLevel: 9, adaptiveFiltering: true });
  } else if (ext === '.webp') {
    image = image.webp({ quality: 85 });
  } else {
    image = image.jpeg({ quality: 85, mozjpeg: true });
  }

  try {
    await image.toFile(temp);
    const after = (await stat(temp)).size;

    if (after < before) {
      await rename(temp, file);
      return { file, before, after };
    }

    await unlink(temp);
    return { file, before, after: before };
  } catch (error) {
    await unlink(temp).catch(() => {});
    throw error;
  }
}

function kb(bytes) {
  return `${(bytes / 1024).toFixed(1)} KB`;
}

let totalBefore = 0;
let totalAfter = 0;
let changed = 0;

for await (const file of images(root)) {
  const result = await compress(file);
  totalBefore += result.before;
  totalAfter += result.after;

  if (result.after < result.before) {
    changed += 1;
    console.log(`${path.relative(process.cwd(), file)}: ${kb(result.before)} -> ${kb(result.after)}`);
  }
}

const saved = totalBefore - totalAfter;
console.log(`\n${changed} files compressed, saved ${kb(saved)} (${kb(totalBefore)} -> ${kb(totalAfter)})`);
