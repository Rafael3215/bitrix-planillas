# bitrix-planillas

Puente gratuito entre Bitrix24 y el dashboard **Entrega de planillas** de Audiomusica Proyectos.

- Cada mañana, la acción **Leer tareas de Bitrix24** (`.github/workflows/leer-bitrix.yml`) consulta en Bitrix24 las tareas cuyo nombre contiene "planilla" y las guarda **cifradas** en `tareas.enc` (AES-256; la clave está en el secreto `DATOS_CLAVE`). Sin la clave el archivo no se puede leer.
- Es **solo lectura**: usa `tasks.task.list` y nunca crea ni modifica nada en Bitrix24.
- La URL del webhook está en el secreto del repositorio `BITRIX_WEBHOOK` (Ajustes → Secretos y variables → Actions). No se guarda en ningún archivo.
- La tarea programada de Claude descarga `tareas.enc`, lo descifra y actualiza el dashboard de lunes a viernes.
- Para ejecutarla a mano: pestaña **Actions** → *Leer tareas de Bitrix24* → **Run workflow**.
- Si falla, GitHub envía un correo al dueño del repositorio.
