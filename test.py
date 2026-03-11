from wasm_vmp import JiexStart

# Initialize and run obfuscator on test_ops.wasm
processor = JiexStart('base64_2.wasm')
processor.parse_module()
processor.encrypt_module('base64_2_vmp.wasm', not_jeb=False)
print("Obfuscation complete: base64_2_vmp.wasm generated")
