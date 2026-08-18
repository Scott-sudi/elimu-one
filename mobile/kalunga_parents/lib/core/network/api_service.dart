import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../config/api_config.dart';
import '../errors/api_exception.dart';
import 'api_response.dart';
import 'auth_interceptor.dart';

/// Client HTTP unique (Dio) pour toute l'application.
///
/// Gère GET / POST / PUT / PATCH / DELETE, timeouts, JSON et mapping d'erreurs.
class ApiService {
  ApiService({
    Dio? dio,
    FlutterSecureStorage? storage,
    void Function()? onSessionExpired,
  }) : _storage = storage ?? const FlutterSecureStorage() {
    _dio = dio ??
        Dio(
          BaseOptions(
            baseUrl: ApiConfig.baseUrl.endsWith('/')
                ? ApiConfig.baseUrl
                : '${ApiConfig.baseUrl}/',
            connectTimeout: ApiConfig.connectTimeout,
            receiveTimeout: ApiConfig.receiveTimeout,
            sendTimeout: ApiConfig.sendTimeout,
            headers: ApiConfig.defaultHeaders,
            responseType: ResponseType.json,
            validateStatus: (status) => status != null && status < 500,
          ),
        );

    _dio.interceptors.add(
      AuthInterceptor(
        storage: _storage,
        dio: _dio,
        onSessionExpired: onSessionExpired,
      ),
    );

    // Logs utiles en debug uniquement.
    assert(() {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: true,
          error: true,
          logPrint: (obj) {
            // ignore: avoid_print
            print(obj);
          },
        ),
      );
      return true;
    }());
  }

  late final Dio _dio;
  final FlutterSecureStorage _storage;

  Dio get client => _dio;
  FlutterSecureStorage get secureStorage => _storage;

  Future<ApiResponse<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    T Function(dynamic raw)? parser,
    bool skipAuth = false,
  }) {
    return _request(
      () => _dio.get(
        path,
        queryParameters: queryParameters,
        options: Options(extra: {'skipAuth': skipAuth}),
      ),
      parser: parser,
    );
  }

  Future<ApiResponse<T>> post<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic raw)? parser,
    bool skipAuth = false,
  }) {
    return _request(
      () => _dio.post(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'skipAuth': skipAuth}),
      ),
      parser: parser,
    );
  }

  Future<ApiResponse<T>> put<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic raw)? parser,
    bool skipAuth = false,
  }) {
    return _request(
      () => _dio.put(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'skipAuth': skipAuth}),
      ),
      parser: parser,
    );
  }

  Future<ApiResponse<T>> patch<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic raw)? parser,
    bool skipAuth = false,
  }) {
    return _request(
      () => _dio.patch(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'skipAuth': skipAuth}),
      ),
      parser: parser,
    );
  }

  Future<ApiResponse<T>> delete<T>(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
    T Function(dynamic raw)? parser,
    bool skipAuth = false,
  }) {
    return _request(
      () => _dio.delete(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(extra: {'skipAuth': skipAuth}),
      ),
      parser: parser,
    );
  }

  Future<ApiResponse<T>> _request<T>(
    Future<Response<dynamic>> Function() call, {
    T Function(dynamic raw)? parser,
  }) async {
    try {
      final response = await call();
      final status = response.statusCode ?? 0;
      final body = response.data;

      if (body is! Map<String, dynamic>) {
        if (status == 404) {
          throw const ServerException(
            'Service temporairement indisponible. Réessayez plus tard.',
            statusCode: 404,
          );
        }
        throw const ParsingException();
      }

      final apiResponse = ApiResponse<T>.fromJson(
        body,
        parseData: parser,
      );

      if (status == 401) {
        throw UnauthorizedException(apiResponse.message);
      }

      if (!apiResponse.success || status >= 400) {
        throw ServerException(
          apiResponse.message.isNotEmpty
              ? apiResponse.message
              : 'Une erreur est survenue.',
          statusCode: status,
          errors: apiResponse.errors,
        );
      }

      return apiResponse;
    } on ApiException {
      rethrow;
    } on DioException catch (e) {
      throw _mapDioException(e);
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ParsingException(e.toString());
    }
  }

  ApiException _mapDioException(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const TimeoutException();
      case DioExceptionType.connectionError:
        return const NetworkException();
      case DioExceptionType.badResponse:
        final status = e.response?.statusCode;
        final data = e.response?.data;
        String message = 'Erreur serveur.';
        Map<String, dynamic>? errors;
        if (data is Map<String, dynamic>) {
          message = data['message']?.toString() ?? message;
          final rawErrors = data['errors'];
          if (rawErrors is Map<String, dynamic>) errors = rawErrors;
        }
        if (status == 401) {
          return UnauthorizedException(message);
        }
        return ServerException(message, statusCode: status, errors: errors);
      case DioExceptionType.cancel:
        return const NetworkException('Requête annulée.');
      default:
        return const NetworkException();
    }
  }
}
