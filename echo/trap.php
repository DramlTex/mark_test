<?php

// Функция для логирования сообщений
function logus($message){
    $logMessage = date('Y-m-d H:i:s') . ' ' . $message; 
    $filePath = __DIR__ . '/../logus/trap.log';
    // Используем LOCK_EX для предотвращения одновременной записи
    file_put_contents($filePath, $logMessage . PHP_EOL, FILE_APPEND | LOCK_EX);
}

// Функция для сохранения вебхука в файл
function save_webhook($content){
    $webhooksDir = __DIR__ . '/webhooks';

    // Проверка существования директории, если нет - создаём её
    if (!is_dir($webhooksDir)) {
        if (!mkdir($webhooksDir, 0755, true)) {
            logus("Не удалось создать директорию webhooks.");
            return false;
        }
    }

    // Генерация имени файла на основе текущей даты и времени до секунды
    $filename = date('Y-m-d_H-i-s') . '.json';
    $filePath = $webhooksDir . '/webhook_' .  $filename;

    // Декодирование содержимого вебхука (предполагается JSON)
    $decodedContent = json_decode($content, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        logus("Ошибка декодирования JSON: " . json_last_error_msg());
        return false;
    }

    // Кодирование содержимого обратно в JSON с форматированием
    $jsonContent = json_encode($decodedContent, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    if ($jsonContent === false) {
        logus("Ошибка кодирования JSON: " . json_last_error_msg());
        return false;
    }

    // Сохранение JSON в файл
    if (file_put_contents($filePath, $jsonContent) === false) {
        logus("Не удалось сохранить вебхук в файл: " . $filePath);
        return false;
    }

    logus("Вебхук успешно сохранён в файл: " . $filePath);
    return $filePath; // Возвращаем путь к сохранённому файлу
}

// Получение данных вебхука, переданных методом POST
$webhookContent = file_get_contents('php://input');

// Проверка на наличие данных
if (!empty($webhookContent)) {
    // Сохранение вебхука в файл
    $savedFilePath = save_webhook($webhookContent);

    if ($savedFilePath !== false) {
        // Абсолютный путь к Python скрипту
        $pythonScriptPath = escapeshellarg(__DIR__ . '/main.py');

        // Получение имени файла из пути
        $filename = basename($savedFilePath);
        $escapedFilename = escapeshellarg($filename);

        // Логирование запуска Python скрипта с передачей имени файла
        logus("Запуск Python скрипта: " . $pythonScriptPath . " с аргументом: " . $escapedFilename);

        // Формирование команды для выполнения без передачи аргументов и логирования вывода
        // Здесь мы передаём имя файла как аргумент Python скрипту
        $mainLogPath = escapeshellarg(__DIR__ . '/../logus/trap.log');
        $cmd = "python3 " . $pythonScriptPath . " " . $escapedFilename . " >> " . $mainLogPath . " 2>&1; echo 'Exit code: $?' >> " . $mainLogPath;

        // Выполнение команды
        exec($cmd, $output, $return_var);

        if ($return_var === 0) {
            logus("Python скрипт успешно запущен.");
        } else {
            logus("Ошибка при запуске Python скрипта. Код возврата: " . $return_var);
        }
    } else {
        logus("Сохранение вебхука не удалось. Python скрипт не запущен.");
    }
} else {
    // Логирование отсутствия данных вебхука
    logus("Данные вебхука не получены.");
}

?>
