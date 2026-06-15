<?php
// Copyright 2026 Google LLC
// PHP backend for the repo_to_market_analyzer UI dashboard.

header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With");

if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit(0);
}

// Helper to send JSON error
function sendError($message, $code = 400) {
    http_response_code($code);
    echo json_encode([
        "success" => false,
        "error" => $message
    ]);
    exit;
}

// Retrieve POST parameters
$input = json_decode(file_get_contents('php://input'), true);
if (!$input) {
    // Fallback to GET for simple testing
    $input = $_GET;
}

$action = isset($input['action']) ? trim($input['action']) : 'full';
$path = isset($input['path']) ? trim($input['path']) : '';
$query = isset($input['query']) ? trim($input['query']) : 'software project';
$tech_stack = isset($input['tech_stack']) ? trim($input['tech_stack']) : '';
$monetization_pattern = isset($input['monetization_pattern']) ? trim($input['monetization_pattern']) : 'Auto';

// Validate inputs
if (in_array($action, ['inspect', 'full']) && empty($path)) {
    sendError("El parámetro 'path' (ruta del repositorio local) es obligatorio.");
}

// Paths
$python_script = __DIR__ . '/.agents/skills/repo_to_market_analyzer/repo_to_market_analyzer.py';
if (!file_exists($python_script)) {
    sendError("El script de Python no se encuentra en la ruta esperada: " . $python_script, 500);
}

// We will use temporary files in the current directory or system temp
$temp_dir = __DIR__ . '/tmp';
if (!file_exists($temp_dir)) {
    mkdir($temp_dir, 0777, true);
}

$id = uniqid();
$inspect_file = $temp_dir . "/inspect_{$id}.json";
$market_file = $temp_dir . "/market_{$id}.json";
$business_file = $temp_dir . "/business_{$id}.json";

$python_cmd = "python"; // Assume python is on PATH. We verified it is Python 3.13.3.

try {
    if ($action === 'inspect') {
        // Run code inspector only
        $cmd = sprintf('%s %s inspect-code --repo-path %s --output %s', 
            $python_cmd, 
            escapeshellarg($python_script), 
            escapeshellarg($path), 
            escapeshellarg($inspect_file)
        );
        $output = shell_exec($cmd . " 2>&1");
        
        if (!file_exists($inspect_file)) {
            sendError("Error al ejecutar inspect-code: " . $output, 500);
        }
        
        $result = json_decode(file_get_contents($inspect_file), true);
        @unlink($inspect_file);
        
        echo json_encode([
            "success" => true,
            "action" => "inspect",
            "data" => $result
        ]);
        
    } elseif ($action === 'research') {
        // Run market research only
        $cmd = sprintf('%s %s research-market --query %s --tech-stack %s --output %s', 
            $python_cmd, 
            escapeshellarg($python_script), 
            escapeshellarg($query), 
            escapeshellarg($tech_stack), 
            escapeshellarg($market_file)
        );
        $output = shell_exec($cmd . " 2>&1");
        
        if (!file_exists($market_file)) {
            sendError("Error al ejecutar research-market: " . $output, 500);
        }
        
        $result = json_decode(file_get_contents($market_file), true);
        @unlink($market_file);
        
        echo json_encode([
            "success" => true,
            "action" => "research",
            "data" => $result
        ]);
        
    } elseif ($action === 'business') {
        // Requires mock/previous files or will use default empty structures
        sendError("La acción 'business' requiere un flujo completo. Use la acción 'full'.");
        
    } elseif ($action === 'full') {
        // Run all three steps sequentially
        
        // 1. Inspect
        $cmd_inspect = sprintf('%s %s inspect-code --repo-path %s --output %s', 
            $python_cmd, 
            escapeshellarg($python_script), 
            escapeshellarg($path), 
            escapeshellarg($inspect_file)
        );
        $out_inspect = shell_exec($cmd_inspect . " 2>&1");
        if (!file_exists($inspect_file)) {
            sendError("Fallo en la Inspección de Código: " . $out_inspect, 500);
        }
        $inspect_data = json_decode(file_get_contents($inspect_file), true);
        
        // Auto-extract tech stack from extensions if empty
        if (empty($tech_stack) && isset($inspect_data['extensions'])) {
            $exts = array_keys($inspect_data['extensions']);
            $techs = [];
            foreach ($exts as $e) {
                $e = trim($e, '.');
                if ($e) $techs[] = $e;
            }
            $tech_stack = implode(',', $techs);
        }
        
        // 2. Research
        $cmd_market = sprintf('%s %s research-market --query %s --tech-stack %s --output %s', 
            $python_cmd, 
            escapeshellarg($python_script), 
            escapeshellarg($query), 
            escapeshellarg($tech_stack), 
            escapeshellarg($market_file)
        );
        $out_market = shell_exec($cmd_market . " 2>&1");
        if (!file_exists($market_file)) {
            @unlink($inspect_file);
            sendError("Fallo en la Investigación de Mercado: " . $out_market, 500);
        }
        $market_data = json_decode(file_get_contents($market_file), true);
        
        // 3. Business Architect
        $cmd_business = sprintf('%s %s business-architect --audit-results %s --market-results %s --monetization-pattern %s --output %s', 
            $python_cmd, 
            escapeshellarg($python_script), 
            escapeshellarg($inspect_file), 
            escapeshellarg($market_file), 
            escapeshellarg($monetization_pattern),
            escapeshellarg($business_file)
        );
        $out_business = shell_exec($cmd_business . " 2>&1");
        if (!file_exists($business_file)) {
            @unlink($inspect_file);
            @unlink($market_file);
            sendError("Fallo en la Estrategia de Negocio: " . $out_business, 500);
        }
        $business_data = json_decode(file_get_contents($business_file), true);
        
        // Clean up
        @unlink($inspect_file);
        @unlink($market_file);
        @unlink($business_file);
        
        // Respond with complete audit results
        echo json_encode([
            "success" => true,
            "action" => "full",
            "audit" => $inspect_data,
            "market" => $market_data,
            "business" => $business_data
        ]);
    } else {
        sendError("Acción no soportada: " . $action);
    }
} catch (Exception $e) {
    sendError("Ocurrió un error excepcional: " . $e->getMessage(), 500);
}
